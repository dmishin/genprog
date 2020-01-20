import assembler

nmead_code = assembler.compile_code("""
################################
#sortarray of first 3 vectors
################################
#start sorting
label 30

# v0 < v1?
vload 0
vless 1
iftrue_down 10 #label 10
#swap v0 <-> v1
vswap 1
label 10
vstore 0    

# v0 < v2 ?
vless 2
iftrue_down 10
#swap v0 <-> v2
vswap 2
vstore 0
label 10

# v1 < v2 ?
vload 1
vless 2
iftrue_down 10
vswap 2
vstore 1

label 10


#############################################################
#     center 
#now find center
vload 0
fload_value 0.5
vmerge 1
vstore 3
#trace

#now v3 is center
#############################################################
#     reflect
fload_value 2
vmerge 2

#accum = 4 is reflected

#now if fr < fbest(0)
vless 0
vstore 4 

iffalse_down 10              # to REFLECT_NOT_BEST
#best case: f(r) < f0

#try extend
fload_value 2
vmerge 3 # accum = 2xr - xc

#is it even lesser
vless 4
iffalse_down 20
#yes, even lesser: use smallest
vstore 2
jump_up 30
label 20
#no, reflect was better
vload 4
vstore 2 #xh := xr
jump_up 30

label 10 # REFLECT_NOT_BEST
vload 4 
vless 1
# if it is lesser than xg
iffalse_down 10   # to REFlECT_BAD
# ok, it is good: not the best, but better than pre-worst
vstore 2
jump_up 30

label 10 #REFlECT_BAD

#is it at least good?
vload 4
vless 2
# if fr < fh
iffalse_down 10  #to SHRINK
# swap reflect and worst
vswap 2
vstore 4

label 10 # SHRINK

vload 3
fload_value 0.5
vmerge 2
# 0.5 xh + 0.5 xc

vless 2 #is it at least better than xh?
iffalse_down 10 #to GLOBAL SHRINK
#ok, at least something
vstore 2
jump_up 30

label 10 #GLOBAL SHRINK
vload 0
fload_value 0.5
vmerge 1
vstore 1
vload 0
vmerge 2
vstore 2
jump_up 30
""")
