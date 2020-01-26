from machine import FunctionTable, CallbackFunction

t = FunctionTable(0)
print(t.evaluate((1.0, 5.0)))

c = CallbackFunction()
c.set(lambda x, y: x+y)

print(c.evaluate((10,10)))
