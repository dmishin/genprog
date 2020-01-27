from machine import FunctionTable, wrapfunc

t = FunctionTable(0)
print(t.evaluate((1.0, 5.0)))

c = wrapfunc(lambda x, y: x+y)

print(c.evaluate((10,10)))
