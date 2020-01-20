CMP=g++ -Wall -Wextra -pedantic -O3 -c -fPIC
LNK=g++
PYCFALGS=$(shell pkg-config --cflags python3)
PYLFLAGS=$(shell pkg-config --libs python3)

.PHONY: test clean
default: _machine.so

machine_wrap.cpp: machine.i
	swig -c++ -python -o machine_wrap.cpp machine.i 

machine_wrap.o: machine_wrap.cpp machine.hpp machinedef_hpp.inl
	$(CMP) -Wno-missing-field-initializers -Wno-missing-braces $(PYCFALGS)  machine_wrap.cpp

_machine.so: machine_wrap.o machine.o
	$(LNK) $(PYLFLAGS) -shared machine_wrap.o machine.o -o _machine.so

machine.o: machine.cpp machine.hpp machinedef_cpp.inl machinedef_hpp.inl
	$(CMP) machine.cpp -o machine.o

test_machine.o: test_machine.cpp machine.cpp machine.hpp machinedef_hpp.inl
	$(CMP) test_machine.cpp -o test_machine.o

test_machine: test_machine.o machine.o
	$(LNK) test_machine.o machine.o -o test_machine

#Generated code
machinedef_hpp.inl: generate_machine.py machinedef.py
	python generate_machine.py
machinedef_cpp.inl: generate_machine.py machinedef.py
	python generate_machine.py

#Testing
test: test_machine
	./test_machine

clean:
	rm machine_wrap.cpp *.so *.o *.so machinedef_???.inl test_machine 

