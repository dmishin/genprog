//%module(directors="1") machine
%module(threads="1") machine
%{
#include "machine.hpp"
#define TEXTIFY(s) _TEXTIFY(s)
#define _TEXTIFY(s) #s
%}

%typemap(in) (const i8 *bytes, size_t array_length) {
    Py_ssize_t len;
    char * pbuffer;
    if (-1==PyBytes_AsStringAndSize($input, &pbuffer, &len)){
      return NULL;
    }
    $1 = reinterpret_cast<i8*>(pbuffer);
    $2 = len;
 }

// Parse vector from tuple
%typemap(in) vec{
  if (PyTuple_Check($input)) {
    if (PyTuple_Size($input) != DIMENSION){
      PyErr_SetString(PyExc_TypeError, "Tuple must have " TEXTIFY(DIMENSION) " values");
      return NULL;
    }
    FOR2(i){
      $1.coord[i] = PyFloat_AsDouble(PyTuple_GetItem($input, i));
      if (PyErr_Occurred()){
	return NULL;
      }
    }
  } else {
    PyErr_SetString(PyExc_TypeError,"expected a tuple.");
    return NULL;
  }
 }

%typemap(in) vec &(vec vtemp){
  $1 = &vtemp;
  if (PyTuple_Check($input)) {
    if (PyTuple_Size($input) != DIMENSION){
      PyErr_SetString(PyExc_TypeError, "Tuple must have " TEXTIFY(DIMENSION) " values");
      return NULL;
    }
    FOR2(i){
      vtemp.coord[i] = PyFloat_AsDouble(PyTuple_GetItem($input, i));
      if (PyErr_Occurred()){
	return NULL;
      }
    }
  } else {
    PyErr_SetString(PyExc_TypeError,"expected a tuple.");
    return NULL;
  }
 }

%typemap(out) vec, const vec & {
  $result = PyTuple_New(DIMENSION);
  FOR2(i){
    PyTuple_SetItem($result, i, PyFloat_FromDouble($1.coord[i]));
  }
 }

typedef signed char i8;

struct point{
  vec x;
  double f;
  bool evaluated;
};

%pythoncode %{
def point_str(self):
    if self.evaluated:
        return "{}:{}".format(self.x, self.f)
    else:
        return "{}:?".format(self.x)
point.__str__ = point_str
del point_str

def wrapfunc(func):
    if not callable(func): raise ValueError("Function mus be callable")
    f = CallbackFunction()
    f._set(func)
    f._function = func	     
    return f	  
%}

%feature("pythonprepend") Machine::set_function(AbstractFunction &) %{
    #fallback support, when functions were unmbers
    if isinstance(f, int): f = FunctionTable(f)
    #store function reference to own the object.
    self._function = f
%}
%feature("pythonappend") Machine::Machine() %{
    self.set_function(FunctionTable(0))
%}
class Machine{
public:
  //working registers state
    point vec_accum;
    double float_accum;
    bool flag;
    //memory
    //point vec_registers[NVECREG];
    //double float_registers[NFLOATREG];
    //comand pointer
    size_t cpr;
    //bytecode, precompiled
    //std::vector<instruction> code;

    //accounting
    size_t nsteps;
    size_t ncalls;
    bool tracing;

    //operations
    //load code and prepare it for running
    void load_code(const i8* bytes, size_t array_length);
    void step();
    %thread;
    void steps(size_t n);
    bool runto(size_t maxsteps, size_t maxevals, vec target, double tol);
    %nothread;
    void reset();
    vec get_vec_reg(size_t i);
    void set_vec_reg(size_t i, const vec&v);
    double get_float_reg(size_t i);
    void set_float_reg(size_t i, double v);
    int get_jump_index(size_t address);
    Machine();
    void set_function(AbstractFunction &f);
    
    void set_trace_live_code(bool t);
    void get_trace_live_code()const;
    bool is_instruction_live(size_t address)const;    
};

class AbstractFunction{
 public:
  AbstractFunction();
  virtual ~AbstractFunction();
  virtual double evaluate(const vec& x)const=0;
};

class FunctionTable: public AbstractFunction{
public:
  FunctionTable(size_t index_);
  virtual ~FunctionTable();
  virtual double evaluate(const vec&x)const;
};

//function pointer type for callback
%{
  static double PythonCallback(double x, double y, void* data)
  {
    PyGILState_STATE state = PyGILState_Ensure();
    PyObject* func = (PyObject*)data;
    PyObject* args = Py_BuildValue("dd", x,y);
    PyObject* res = PyEval_CallObject(func, args);
    double dres;
    Py_DECREF(args);
    if (res){
      dres = PyFloat_AsDouble(res);
    }else{
      dres = -1;
    }
    Py_XDECREF(res);
    PyGILState_Release(state);
    return dres;
  }
%}

typedef double (*TFunc)(double, double, void*);
class CallbackFunction: public AbstractFunction{
public:
  CallbackFunction();
  virtual ~CallbackFunction();
  virtual double evaluate(const vec& x)const;
};

%addmethods CallbackFunction{
  void _set(PyObject* pyfunc){
    //This method would not increase reference count of the function; it is handled by the wrapfunc function
    self->callback = &PythonCallback;
    self->userdata = (void*)pyfunc;
  }
}

void randomize();
const char* command_system_hash();
