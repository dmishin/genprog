from machine import randomize, Machine, FunctionTable
import random
from nmead import nmead_code

initial_genome_range = (50, 1500)
mutate_percent = 0.05
maxgenome = 500

def create_individual():
    if random.random() < 0.01:
        return nmead_code
    genomelen = random.randint(*initial_genome_range)
    return bytes([random.randint(0, 255) for _ in range(genomelen//2*2)])

average_attempts = 1
def fitness(genome, expected=(1.0,1.0)):
    
    norms = 0.0
    evals = 0.0
    steps = 0.0

    m = Machine()
    m.set_function(FunctionTable(input_data['func_index']))
    assert isinstance(genome, bytes)
    m.load_code(genome)

    for i in range(average_attempts):
        if i != 0: m.reset()
        reached = m.runto(maxsteps=input_data['maxsteps'],
                          maxevals=input_data['maxevals'],
                          target=expected,
                          tol=input_data['tol'])
                          
        norm = sum(abs(xi-x0i) for xi, x0i in zip(expected, m.get_vec_reg(0)))
        if norm != norm:
            norm = 1e100
            
        evals += m.ncalls
        steps += m.nsteps

        main = 0.0 if reached else -norm
        
        if m.ncalls < 10:
            main -= 10.0 * (10-m.ncalls)
        norms += main
        
    return ( norms / average_attempts,
             -evals/ average_attempts,
             -steps/ average_attempts,
             -len(genome) ) #allow 100 bytes for free

crossover_signature_len = 6
crossover_search_radius = 12
def crossover(parent_1, parent_2):
    """Crossover (mate) two parents to produce two children.

    :param parent_1: candidate solution representation (list)
    :param parent_2: candidate solution representation (list)
    :returns: tuple containing two children

    """
    index1 = random.randrange(0, len(parent_1)) if parent_1 else 0

    def similarity(bytes1, bytes2):
        return sum(abs(b1-b2) for b1,b2 in zip(bytes1, bytes2))/min(len(bytes1),len(bytes2))

    crossover_signature = parent_1[index1:index1+crossover_signature_len]

    search_range = range(max(0, index1-crossover_search_radius),
                       min(len(parent_2), index1+crossover_search_radius))
    if len(search_range) == 0:
        index2 = random.randint(0,len(parent_2)-1)
    else:
        index2 = min(search_range,
                     key = lambda idx: similarity(crossover_signature,
                                                  parent_2[idx:idx+crossover_signature_len]))
    
    child_1 = parent_1[:index1] + parent_2[index2:]
    child_2 = parent_2[:index1] + parent_1[index2:]
    return child_1, child_2

from numpy.random import exponential
average_mutation_len = 1
mutate_percent = 0.02
average_duplication_len = 10

def mutate(individual):
    """Reverse the bit of a random index in an individual."""

    def even_rand(avg):
        return round(exponential(avg/2))*2+2
    def any_rand(avg):
        return round(exponential(avg))+1
    def random_data(l):
        return [random.randint(0,255) for _ in range(l)]
    def mutate_once(values):
        #mutation type: insert/delete/replace/duplicate
        mut_type = random.randint(0,3)
        if 0<=mut_type<=2:
            #mut_length = round(exponential(average_mutation_len/2-1))*2+2            
            mut_position = random.randint(0,len(values))
            if mut_type==0:
                values[mut_position:mut_position] = random_data(even_rand(average_mutation_len))
            elif mut_type==1:
                mut_length = any_rand(average_mutation_len)
                values[mut_position:mut_position+mut_length] = random_data(mut_length)
            elif mut_type==2:
                del values[mut_position:mut_position+even_rand(average_mutation_len)]
            else: assert False
        elif mut_type==3:
            mut_length = even_rand(average_duplication_len)
            source_pos = random.randint(0,len(values)//2)*2
            insert_pos = random.randint(0,len(values)//2)*2
            values[insert_pos:insert_pos] = values[source_pos:source_pos+mut_length]
        else: assert False
        #print("Mutate:",mut_type)
    
    individual = list(individual)
    num_mutations = round(exponential(len(individual)*mutate_percent))+1
    for _ in range(num_mutations):
        mutate_once(individual)
    return bytes(individual)

poolsize = 1000
topsize = 300

genome = [create_individual() for _ in range(poolsize)]
import random


def makenew():
    key = random.randint(0,10)
    if key == 0:
        return (create_individual(),)
    elif 1<=key<=5:
        return (mutate(random.choice(fgenome)[1]),)
    elif 6<=key<=10:
        return crossover(random.choice(fgenome)[1],
                         random.choice(fgenome)[1])
    else:
        raise ValueError(key)

class IndividualBase(object):
    def __init__(self, genome):
        self.genome = genome
        self.fitness = None
        
class Individual(IndividualBase):
    def __init__(self, genome):
        super().__init__(genome)
        self.machine = Machine()
        self.machine.load_code(genome)
        
if __name__=="__main__":
    randomize()
    input_data = {'func_index':0,
                  'maxsteps':10000,
                  'maxevals':1000,
                  'tol':0.00001,
                  'orphan_len':1000}
    expected_point = (1.0, 1.0)
    
    gen = 0
    while True:
        gen += 1
        fgenome = [(fitness(g, expected_point),g) for g in genome]
        fgenome.sort(key = lambda ab:ab[0], reverse=True)
        fgenome = fgenome[:topsize]
        #if gen%100 == 0:
        print(gen,"\t",fgenome[0])

        genome = [g for f,g in fgenome]
        while len(genome) < poolsize:
            for new in makenew():
                genome.append(new[:maxgenome])

if __name__=="__main__1":
    code = b'\xcel\xd5\xfau.\x8c\x1ecJus\xca\xa4\xb6\x98\xa0\xe1\x07\xbew\x01c\xa4\xc9.w\x1ec#\x99##*/K\xb1\xe1\xa2K\xb1\xe1\xe3\x84.@\xab@\xab@\x81\xe8V\xe1\xe1@\xe1\xaf@\xe1\xe3\xaf@\xe1\x06K\x1d\x9d\x13E\xafg\x13\xc3}\xa2\xe7\xe59\x94ob9\x94obR4|q\xa7\xea\x93\r\xa2\xe7\x00"\xe54\xe54\xa2\xe7\xe54\xe54\xe54\xe54\xe5\xe7\xe54\xe54\xe54\xe54\xe54\xe54\xe5\x99\xe54\xe54\xe5\xe7\xe54\xe54\xe5\x99;4\xe54\xa2\xe7\xe5\x9e;:\xac\xf044\x0b4\xe54\xe5\x99;4\xe54\xa2\xe7\xe5\x9e;4\xe5\x99;4\x0b4\xe54\xe5\x99;4\x0b4\xe54\xe5\x99;4\xe54\xa24\xe54\xa2\xe7\xe54\xa24\xe54\xa24;4\xe54\xa2\xe7\xe54\xe54\xa24\xe54\xa2\xe7\xe54\xe54\xe5\x99;4\xe54\xa2\xe7\xe5\xea|q\xa7\xea|\x84\xa7\xea|\x84\x88@\x88@\x885\xe7@\x88\x84s\xc1\xd5\x84\xe7@\x88\x84s\xc1\xd5\x84s3\xaf@\xe1\xaf\x91\xdao\xd5\x84\x84@\xe1\xe5:\xb3\x893\xe1\xaf\x91\\o\xd5\x84@\xe1\xaf\x91\\o\xd5\x84@\xe1\xaf\x91\\o\xd5\x84@\xe1\xaf\x91\\o\xd5\x84s@\xe1\xab\\o\xd5\xcf\xe5:(\x84\xe7\xb1@\xe1\xec\x9d:(\x84\xe7\x9e;@\xd5I\xf1\x06K\x1d\x9d\x1e\xcd\xf5u|\nH\x94\xa2\xe7\xd1\rg\x13\xc9\xe7@\xe1\xe3\xfb\x9e;@\xaf@\xe1\xaf\x91\\o\xd5\x84@\xe1\xaf\x91\\\xd5I\xf1\x06K\x1d707\x1b`\x89\xac\x83^i%\xd6\x98\xe6\xad\x16|\xf65i\x98\xe6\xadi%\xdf0\xe6\xce7\xacu\xad\x16|\xf65i\xad\x16|\xf65i\x98\xe6\xad\xd8\xbd\xdf0\xe65i\x98\xe6\xad\xd8\xbd\xdf0\xe6\xce7\xacu\xadi%\xe1_i%\x1a5i\xc7I\xcb\x1a\xbc\xc5\xe9\xbbq\xf8e\xcee\xca+\xce\x10S6\xac\xeb'
    #code=nmead_code
    randomize()
    input_data = {'func_index':0,
                  'maxsteps':10000,
                  'maxevals':1000,
                  'tol':0.00001,
                  'orphan_len':1000}
    expected_point = (1.0, 1.0)
    print("FItness for func index",input_data['func_index'])
    print(fitness(code, expected_point))
    input_data = {'func_index':1,
                  'maxsteps':10000,
                  'maxevals':1000,
                  'tol':0.00001,
                  'orphan_len':1000}
    expected_point = (0.0, 0.0)
    print("FItness for func index",input_data['func_index'])
    print(fitness(code, expected_point))

    input_data = {'func_index':2,
                  'maxsteps':10000,
                  'maxevals':1000,
                  'tol':0.00001,
                  'orphan_len':1000}
    expected_point = (1.0, 2.0)
    print("FItness for func index",input_data['func_index'])
    print(fitness(code, expected_point))
    
