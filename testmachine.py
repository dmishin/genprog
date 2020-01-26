import machine
import nmead

machine.randomize()
m = machine.Machine()
f = machine.wrapfunc(lambda x,y: (x-5)**2+(y-3)**2)
print("try evaluate:", f.evaluate((10,10)))
m.set_function(f)

m.load_code(nmead.nmead_code)
for i in range(100):
    m.step()

print(m.vec_accum.x)
print(m.get_float_reg(0))
print(m.get_vec_reg(1000))
print(m.vec_accum)
m.vec_accum.x=(10.0, 11.0)

print(m.vec_accum)

