#ifndef GENETIC_OPTIM_INCLUDED
#define GENETIC_OPTIM_INCLUDED

#include <iostream>
#include <vector>
#include <map>
#include <algorithm>
#include <cmath>
#include <ctime>
#include <string>
#include <sstream>

#ifdef MSVCPP
# define GENOPTEXPORT __declspec(dllexport)
#else
# define GENOPTEXPORT
#endif

#define DIMENSION 2
#define FOR2(var) for(size_t var=0;var!=DIMENSION;++var)
struct vec{
  double coord[DIMENSION];
  vec(){}
  vec(const vec&v)
  {
    FOR2(i){coord[i]=v.coord[i];}
  }
  
  vec& operator=(const vec&v){
    FOR2(i){coord[i]=v.coord[i];}
    return *this;
  }
    
  vec &operator *= (double k){
    FOR2(i){coord[i]*=k;};
    return *this;
  }
  vec &operator += (const vec &that){
    FOR2(i){coord[i]+=that.coord[i];};
    return *this;
  }
  vec &add_scaled(double k, const vec&that){
    FOR2(i){coord[i]+=k*that.coord[i];};
    return *this;
  }
  vec &operator -= (const vec &that){
    FOR2(i){coord[i]-=that.coord[i];};
    return *this;
  }
  vec operator + (const vec& that)const{
    vec res(*this);
    res += that;
    return res;
  }
  vec operator * (double k)const{
    vec res(*this);
    res *= k;
    return res;
  }
  vec operator - (const vec& that)const{
    vec res(*this);
    res -= that;
    return res;
  }
};

std::ostream & operator << (std::ostream&os, const vec&v);
double norm(const vec&v);

struct point{
  vec x;
  double f;
  bool evaluated;
  void set(const vec&v){x=v; evaluated=false;};
};

std::ostream & operator << (std::ostream&os, const point&p);

enum argument_type{
		   arg_no,
		   arg_float_value,
		   arg_float_register,
		   arg_vec_register,
		   arg_label
};
typedef signed char i8;

//this include defines command type
#include "machinedef_hpp.inl"

struct instruction{
  command cmd;
  union{
    double arg_float;
    int arg_index;
    i8 arg_label;
    size_t arg_address;
  };
};
std::ostream &operator <<(std::ostream &os, const instruction &cp);

class AbstractFunction{
public:
  AbstractFunction(){};
  virtual ~AbstractFunction(){};
  virtual double evaluate(const vec& x)const=0;
};

class FunctionTable: public AbstractFunction{
public:
  size_t index;
  FunctionTable(size_t index_):index(index_){};
  virtual ~FunctionTable(){};
  virtual double evaluate(const vec&x)const;
};

class Machine{
public:
  //working registers state
  point vec_accum;
  double float_accum;
  bool flag;
  //memory
  point vec_registers[NVECREG];
  double float_registers[NFLOATREG];
  bool vec_registers_changed[NVECREG];
  //comand pointer
  size_t cpr;
  //bytecode, precompiled
  std::vector<instruction> code;

  //accounting
  size_t nsteps;
  size_t ncalls;

  //number of the test function
  AbstractFunction *objective;
  bool tracing;

  //operations
  //load code and prepare it for running
  void load_code(const i8* bytes, size_t size);
  void step();
  void steps(size_t n);
  bool runto(size_t maxsteps, size_t maxevals, const vec& target, double tol);
  Machine();
  std::ostream &show(std::ostream &os)const;
  void set_function(AbstractFunction &f){ objective = &f; };
  void reset();
  //interface for swig mainly
  vec& get_vec_reg(size_t i){ return vec_registers[i%NVECREG].x; };
  void set_vec_reg(size_t i, const vec&v){ vec_registers[i%NVECREG].set(v); };
  double get_float_reg(size_t i)const{ return float_registers[i%NFLOATREG]; };
  void set_float_reg(size_t i, double v){ float_registers[i%NFLOATREG]=v; };
  int get_jump_index(size_t address);
private:
  //pre-calculated list of labels
  std::vector<std::pair<size_t, i8> > labels;
  void prepare_labels();
  
private:
  double eval_function(const vec &v);
  void evaluate(point &p);
  void map_jumps();
  size_t find_label(size_t start, i8 label, int direction)const;
  void trace(const std::string & msg)const;
};

std::ostream & operator <<(std::ostream &os, const Machine &m);

extern "C"{
  void GENOPTEXPORT randomize();
}

#endif //GENETIC_OPTIM_INCLUDED
