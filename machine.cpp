#include "machine.hpp"


#define TRACE(x) {std::cerr<<x;}

double norm(const vec&v){
  double s=0.0;
  FOR2(i){
    s += fabs(v.coord[i]);
  }
  return s;
}

std::ostream & operator << (std::ostream&os, const vec&v){
  os<<"{";
  FOR2(i){
    if (i>0)
      os<<",";
    os<<v.coord[i];
  }
  os<<"}";
  return os;
}

std::ostream & operator << (std::ostream&os, const point&p){
  os << p.x;
  if (! p.evaluated){
    os << ":?";
  }else{
    os << ":" << p.f;
  }
  return os;
}

std::ostream &operator <<(std::ostream &os, const instruction &cp){
  os<<cp.cmd<<"{f:"<<cp.arg_float<<" i:"<<cp.arg_index<<" lab:"<<(int)cp.arg_label<<" addr:"<<cp.arg_address<<"}";
  return os;
}


double sqr(double x){ return x*x; }
double rozen(double x, double y){
  return sqr(x) + 20*sqr(y+1-sqr(x+1));
}

#define MTRACE(msg) {if (tracing){ std::ostringstream oss; oss<<msg<<std::endl; trace(oss.str()); }}
#include "machinedef_cpp.inl"

void Machine::trace(const std::string & msg)const
{
  if (tracing) std::cout<<msg;
}

//trace command to use inside the machine
//don't do anything is tracing is disabled

double Machine::eval_function(const vec &v)
{
  if (objective) return objective->evaluate(v);
  else {
    std::cerr<<"Function is NULL"<<std::endl;
    throw std::logic_error("Function not specified");
  }
}

double random_float()
{
  return 2.0*(float(rand())/RAND_MAX)-1.0;
}
void random_vec(vec&v)
{
  FOR2(i){v.coord[i] = random_float();};
}
void random_point(point&p)
{
  random_vec(p.x);
  p.evaluated =false;
}

Machine::Machine()
  :objective(NULL)
  ,tracing(false)
{
  reset();
}
void Machine::reset()
{
  float_accum = 0.0;
  flag = false;
  cpr = 0;
  nsteps = 0;
  ncalls = 0;    
  random_point(vec_accum);
  for(size_t i=0;i<NVECREG;++i){
    random_point(vec_registers[i]);
    vec_registers_changed[i]=true;
  }
  for(size_t i=0;i<NFLOATREG;++i)
    float_registers[i] = 0;
}


std::ostream &Machine::show(std::ostream &os)const
{
  using namespace std;
  os<<"Machine T="<<nsteps<<" CP="<<cpr<<endl;
  os<<"  float accum="<<float_accum<<" vec accum="<<vec_accum<<endl;
  os<<"  flag ="<<flag<<endl;
  os<<"  Float registers:"<<endl;
  for(size_t i=0;i<NFLOATREG;i+=4){
    os<<"   "<<i<<")";
    for(size_t j=0;j<4;++j){
      os<<"\t"<<float_registers[i+j];
    }
    os<<endl;
  };
  os<<"  Vec registers:"<<endl;
  for(size_t i=0;i<NVECREG;++i){
    os<<"    "<<i<<") "<<vec_registers[i]<<endl;
  };
  return os;
}
std::ostream & operator <<(std::ostream &os, const Machine &m) {return m.show(os);}

//ensure point is evaluated
void Machine::evaluate(point &p)
{
  if (!p.evaluated){
    p.f = eval_function(p.x);
    p.evaluated = true;
    ncalls += 1;
  }
}

//load code from bytes
double byte2float(i8 x){
  //172/32 ... -4
  return double(x)/32.0;
}

i8 float2byte(double x){
  return (i8)(x * 32.0);
}

void Machine::load_code(const i8* bytes, size_t size)
{
  //must be cleared, because jump mapping would garble it otherwise
  code.clear();
  code.reserve(size/2);
  //load bytes to code. Ensures that result is correct code.
  for(size_t i=0; i+1 < size; i += 2){
    command cmd = (command)(((const unsigned char*)bytes)[i] % cmd_max);
    i8 arg=bytes[i+1];
    instruction cp;
    cp.cmd = cmd;
    switch(get_argument_type(cmd)){
    //NOP commands
    case arg_no:
      break;
    //REGISTER commands
    case arg_float_register:
      cp.arg_index = ((unsigned char)arg)%NFLOATREG;
      break;
    case arg_vec_register:
      cp.arg_index = ((unsigned char)arg)%NVECREG;
      break;
    //FLOAT arg commands
    case arg_float_value:
      cp.arg_float = byte2float(arg);
      break;
    //LABEL commands
    case arg_label:
      cp.arg_label = arg;
      break;
    }
    code.push_back(cp);
  }
  //change labels to jump indices in instructions
  map_jumps();
}

void print_jump_map(const Machine &m, std::ostream&os)
{
  os<<"{";
  bool first=true;
  for(size_t i=0; i!=m.code.size(); ++i){
    switch(m.code[i].cmd){
    case cmd_jump_up:
    case cmd_iftrue_up:
    case cmd_iffalse_up:
    case cmd_jump_down:
    case cmd_iftrue_down:
    case cmd_iffalse_down:
      if (!first) os <<", ";
      else first=false;
      os<<i<<":"<<m.code[i].arg_address;
    default:
      break;
    }
  }
  os<<"}";
}

void Machine::prepare_labels()
{
  for(size_t i=0; i!=code.size(); ++i){
    if (code[i].cmd==cmd_label){
      labels.push_back(std::make_pair(i, code[i].arg_label));
    }
  }
}

int get_jump_dir(command cmd){
  switch(cmd){
  case cmd_jump_up:
  case cmd_iftrue_up:
  case cmd_iffalse_up:
    return -1;
    
  case cmd_jump_down:
  case cmd_iftrue_down:
  case cmd_iffalse_down:
    return 1;
  default:
    return 0;
 }
}
void Machine::map_jumps()
{
  prepare_labels();
  for(size_t i=0; i!=code.size(); ++i){
    int jdir = get_jump_dir(code[i].cmd);
    if (jdir==0) continue;
    code[i].arg_address = find_label(i, code[i].arg_label, jdir);
  }
  if(tracing){
    std::ostringstream os;
    print_jump_map(*this, os);
    os<<std::endl;
    trace(os.str());
  }
}

int Machine::get_jump_index(size_t address)
{
  if(address >= code.size()) return -1;
  if (get_jump_dir(code[address].cmd)==0)
    return -1;
  else
    return static_cast<int>(code[address].arg_address);
}

int label_dist(i8 a, i8 b)
{
  unsigned char diff = (unsigned char)(a ^ b);
  int d = 0;
  while(diff){
    d += diff % 2;
    diff /= 2;
  }
  return d;
}

/**Calculate fitness of given label instruction to the JUMP instruction
   returns pair: distance (in jump direction), label matching
 */
std::pair<int,size_t> label_fitness(const std::pair<size_t, i8> &label, size_t from, i8 jumplabel, bool forward, size_t code_size)
{
  //jump distance is
  //int(label.first) - int(from)
  int d = static_cast<int>(label.first)-static_cast<int>(from);
  if (!forward) d = -d;
  return std::make_pair(label_dist(label.second, jumplabel),
			static_cast<size_t>((d+code_size)%code_size));
}
  
size_t Machine::find_label(size_t start, i8 label, int direction)const{
  //old code
  /*
  size_t i=start;
  size_t best_i = start;
  int best_dist = 1000;
  while (true){
    i = (i+direction+code.size())%code.size();
    if (i==start) break;
    if (code[i].cmd != cmd_label) continue;
    int dist = label_dist(label, code[i].arg_label);
    if(dist < best_dist){
      best_dist = dist;
      best_i = i;
    }
    if (best_dist == 0)
      break;
  }
  return best_i;
  */
  //new code
  std::pair<int,size_t> best_fitness;
  size_t best_address=start;
  bool has_best=false;
  
  for(size_t i=0; i!=labels.size(); ++i){
    std::pair<int,size_t> fitness = label_fitness(labels[i], start, label, direction==1, code.size());
    if (!has_best){
      has_best=true;
      best_fitness = fitness;
      best_address = labels[i].first;
    }else if(fitness < best_fitness){
      best_fitness = fitness;
      best_address = labels[i].first;
    }
  }
  //std::cout<<"Jump from "<<start<<" label:"<<(int)label<<" to:"<<best_address<<std::endl;
  return best_address;
}

void Machine::steps(size_t n)
{
  for(size_t i=0;i!=n;++i){
    step();
  }
}
bool Machine::runto(size_t maxsteps, size_t maxevals, const vec& target, double tol)
{
  while(nsteps < maxsteps && ncalls < maxevals){
    if (vec_registers_changed[0]){
      vec_registers_changed[0] = false;
      if (norm(vec_registers[0].x-target) <= tol){
	return true;
      }
    }
    step();
  }
  return false;
}
void randomize(){
  srand(time(NULL));
}


double FunctionTable::evaluate(const vec&v)const
{
  double x = v.coord[0],
    y = v.coord[1];
  
  switch(index % 4){
  case 0:
    return rozen(x-1,y-1);
  case 1:
    return rozen(x,y);
  case 2:
    return rozen(y-2,x-1);
  case 3:
    return x*x+y*y;
  }
  return 0;
}
