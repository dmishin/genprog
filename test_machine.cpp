#include "acutest.h"
#include "machine.hpp"


void test_machine()
{
  Machine m;
  i8 code[]={ (i8)cmd_nop, 0, (i8)cmd_nop, 0 };
  m.load_code(code, 4);
  m.step();
  TEST_CHECK_(m.cpr==1, "Actual is %d", m.cpr); 
}


TEST_LIST = {
    { "test_machine", test_machine },
    { NULL, NULL }
};
