import random
import json
from numpy.random import exponential
from machine import randomize, Machine, FunctionTable, command_system_hash

initial_genome_range = (50, 1500)
mutate_percent = 0.05
maxgenome = 500
average_mutation_len = 1
mutate_percent = 0.02
average_duplication_len = 10
crossover_signature_len = 6
crossover_search_radius = 12

def create_individual():
    genomelen = random.randint(*initial_genome_range)
    return bytes([random.randint(0, 255) for _ in range(genomelen//2*2)])

class Fitness:
    def __init__(self,
                 maxsteps=10000,
                 maxevals=1000,
                 tol=1e-5,
                 average_attempts=100):
        
        self.maxsteps = maxsteps
        self.maxevals = maxevals
        self.tol = tol
        self.average_attempts = average_attempts
        
    def __call__(self, genome, func, expected):
        assert isinstance(genome, bytes)
        norms = 0.0
        evals = 0.0
        steps = 0.0

        m = Machine()
        m.set_function(func)
        m.load_code(genome)

        for i in range(self.average_attempts):
            if i != 0: m.reset()
            reached = m.runto(maxsteps=self.maxsteps,
                              maxevals=self.maxevals,
                              target=expected,
                              tol=self.tol)
            norm = sum(abs(xi-x0i) for xi, x0i in zip(expected, m.get_vec_reg(0)))
            if norm != norm:
                norm = 1e100
            evals += m.ncalls
            steps += m.nsteps
            main = 0.0 if reached else -norm
            if m.ncalls < 10:
                main -= 10.0 * (10-m.ncalls)
            norms += main

        return ( norms / self.average_attempts,
                 -evals/ self.average_attempts,
                 -steps/ self.average_attempts,
                 -len(genome) ) #allow 100 bytes for free
        
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
    from itertools import cycle, islice
    from utils import load_code
    poolsize = 1000
    topsize = 300

    initial = ["nmead.json"]
    
    if not initial:
        #random initilization
        genome = [create_individual() for _ in range(poolsize)]
    else:
        #non-random init
        initial_genomes = [load_code(fname) for fname in initial]
        genome = list(islice(cycle(initial_genomes), poolsize))
        
    randomize()
    
    fitness = Fitness(maxsteps = 10000,
                      maxevals = 1000,
                      tol = 1e-5)
    func, expected  = FunctionTable(0), (1.0,1.0)

    print(json.dumps({'experiment':{
        'poolsize': poolsize,
        'topsize': topsize,
        'maxsteps': fitness.maxsteps,
        'maxevals': fitness.maxevals,
        'tol': fitness.tol,
        'average_attempts': fitness.average_attempts,
        'initial_population': initial,
        'initial_genome_range': initial_genome_range,
        'mutate_percent': mutate_percent,
        'maxgenome': maxgenome,
        'average_mutation_len': average_mutation_len,
        'mutate_percent': mutate_percent,
        'average_duplication_len': average_duplication_len,
        'crossover_signature_len': crossover_signature_len,
        'crossover_search_radius': crossover_search_radius,
        'command_system_hash': command_system_hash()
    }}))
        
    
    gen = 0
    while True:
        gen += 1
        fgenome = [(fitness(g, func, expected),g) for g in genome]
        fgenome.sort(key = lambda ab:ab[0], reverse=True)
        fgenome = fgenome[:topsize]
        #if gen%100 == 0:
        #print(gen,"\t",fgenome[0])
        f, genome = fgenome[0]
        print(json.dumps({
            'generation': gen,
            'fitness': f,
            'hexcode': genome.hex(),
            'command_system_hash': command_system_hash()
        }))

        genome = [g for f,g in fgenome]
        while len(genome) < poolsize:
            for new in makenew():
                genome.append(new[:maxgenome])
