from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

class ABAFramework:
    def __init__(self, language=None, assumptions=None, contraries=None, rules=None, preferences=None):
        self.language = language or set()
        self.assumptions = assumptions or set()
        self.contraries = contraries or {}
        self.rules = rules or []
        self.preferences = preferences or []
        
    def convert_to_atomic(self):
        atomic_aba = ABAFramework()
        new_language = set(self.language)
        new_assumptions = set(self.assumptions)
        literal_to_new_assumption = {}
        new_rules = []
        
        non_assumption_literals_in_bodies = set()
        for rule in self.rules:
            for premise in rule['premises']:
                if premise not in self.assumptions:
                    non_assumption_literals_in_bodies.add(premise)
        
        for literal in non_assumption_literals_in_bodies:
            new_assumption = f"{literal}_d"
            literal_to_new_assumption[literal] = new_assumption
            new_language.add(new_assumption)
            new_assumptions.add(new_assumption)
            new_rules.append({
                'name': f"der_{literal}",
                'conclusion': new_assumption,
                'premises': [literal]
            })
    
        for rule in self.rules:
            new_premises = []
            for premise in rule['premises']:
                if premise in self.assumptions:
                    new_premises.append(premise)
                else:
                    new_premises.append(literal_to_new_assumption[premise])
            
            new_rules.append({
                'name': f"atom_{rule['name']}",
                'conclusion': rule['conclusion'],
                'premises': new_premises
            })
        
        new_contraries = self.contraries.copy()
        atomic_aba.language = new_language
        atomic_aba.assumptions = new_assumptions
        atomic_aba.contraries = new_contraries
        atomic_aba.rules = new_rules
        atomic_aba.preferences = self.preferences.copy()
        
        return atomic_aba

    def generate_arguments_optimized(self, max_iterations=100):
        arguments = []
        for assumption in self.assumptions:
            arguments.append((assumption, {assumption}))
        
        iteration = 0
        changed = True
        
        while changed and iteration < max_iterations:
            changed = False
            iteration += 1
            current_args = arguments.copy()
            
            for rule in self.rules:
                conclusion = rule['conclusion']
                premises = rule['premises']
                valid_combinations = self._find_valid_combinations(premises, current_args)
                
                for support_args in valid_combinations:
                    full_support = set()
                    for arg in support_args:
                        full_support.update(arg[1])
                    
                    new_arg = (conclusion, frozenset(full_support))
                    if new_arg not in arguments:
                        arguments.append(new_arg)
                        changed = True
        
        return arguments

    def _find_valid_combinations(self, premises, arguments):
        if not premises:
            return [[]]
        
        args_by_conclusion = {}
        for arg in arguments:
            if arg[0] not in args_by_conclusion:
                args_by_conclusion[arg[0]] = []
            args_by_conclusion[arg[0]].append(arg)
        
        for premise in premises:
            if premise not in args_by_conclusion:
                return []
        
        from itertools import product
        premise_args = [args_by_conclusion[p] for p in premises]
        combinations = []
        for combo in product(*premise_args):
            combinations.append(list(combo))
        
        return combinations

    def get_contrary(self, assumption):
        return self.contraries.get(assumption)
    
    def get_preference_relation(self, assumption1, assumption2):
        if (assumption1, assumption2) in self.preferences:
            return 1
        elif (assumption2, assumption1) in self.preferences:
            return -1
        else:
            return 0

    def compute_standard_attacks(self, arguments):
        attacks = []
        for i, (conc1, supp1) in enumerate(arguments):
            for j, (conc2, supp2) in enumerate(arguments):
                if i == j:
                    continue
                for assumption in supp2:
                    contrary = self.get_contrary(assumption)
                    if contrary and contrary == conc1:
                        attacks.append({
                            'type': 'standard',
                            'from': i,
                            'to': j,
                            'via_assumption': assumption,
                            'description': f"Argument {i} ({conc1}) attacks Argument {j} via assumption '{assumption}'"
                        })
        return attacks
    
    def compute_normal_attacks(self, arguments, standard_attacks):
        normal_attacks = []
        for attack in standard_attacks:
            attacker_idx = attack['from']
            target_assumption = attack['via_assumption']
            attacker_arg = arguments[attacker_idx]
            _, attacker_support = attacker_arg
            
            attack_valid = True
            for assump in attacker_support:
                if self.get_preference_relation(assump, target_assumption) == -1:
                    attack_valid = False
                    break
            
            if attack_valid:
                normal_attacks.append({
                    'type': 'normal',
                    'from': attacker_idx,
                    'to': attack['to'],
                    'via_assumption': target_assumption,
                    'description': f"Normal Attack: Argument {attacker_idx} → Argument {attack['to']} (via '{target_assumption}')"
                })
        return normal_attacks

    def compute_reverse_attacks(self, arguments):
        reverse_attacks = []
        for i, (conc_i, supp_i) in enumerate(arguments):
            for j, (conc_j, supp_j) in enumerate(arguments):
                if i == j:
                    continue
                for x in supp_i:
                    contrary_x = self.get_contrary(x)
                    if contrary_x and contrary_x == conc_j:
                        for y_prime in supp_j:
                            if self.get_preference_relation(y_prime, x) == -1:
                                reverse_attacks.append({
                                    'type': 'reverse',
                                    'from': i,
                                    'to': j,
                                    'target_assumption': x,
                                    'weak_assumption': y_prime,
                                    'description': f"Reverse Attack: Argument {i} → Argument {j} - Y attacks X via '{conc_j}'=C('{x}') but y'='{y_prime}' < x='{x}'"
                                })
                                break
        return reverse_attacks

    def compute_all_attacks(self, arguments):
        standard_attacks = self.compute_standard_attacks(arguments)
        normal_attacks = self.compute_normal_attacks(arguments, standard_attacks)
        reverse_attacks = self.compute_reverse_attacks(arguments)
        all_attacks = normal_attacks + reverse_attacks
        
        return {
            'standard': standard_attacks,
            'normal': normal_attacks, 
            'reverse': reverse_attacks,
            'all_aba_plus': all_attacks
        }
    
    def convert_to_non_circular(self):
        """
        Transforme le cadre ABA en version non-circulaire D∘
        """
        if not hasattr(self, 'is_circular'):
            raise NotImplementedError("La méthode 'is_circular' n'est pas définie pour cette instance.")
        
        if not self.is_circular():
            print("Le cadre n'est pas circulaire, aucune transformation nécessaire")
            return self
        
        non_circular_aba = ABAFramework()
        L_minus_A = self.language - self.assumptions
        k_max = len(L_minus_A)
        
        # Étape 1: Créer le nouveau langage
        new_language = set(self.assumptions.copy())
        for literal in L_minus_A:
            for k in range(1, k_max + 1):
                new_literal = f"{literal}^{k}"
                new_language.add(new_literal)
        
        non_circular_aba.language = new_language
        non_circular_aba.assumptions = self.assumptions.copy()
        non_circular_aba.contraries = self.contraries.copy()
        non_circular_aba.preferences = self.preferences.copy()
        
        # Étape 2: Transformer les règles
        new_rules = []
        for rule in self.rules:
            conclusion = rule['conclusion']
            premises = rule['premises']
            
            if conclusion in self.assumptions:
                new_rules.append(rule)
            else:
                for k in range(1, k_max + 1):
                    new_conclusion = f"{conclusion}^{k}"
                    new_premises = []
                    for premise in premises:
                        if premise in self.assumptions:
                            new_premises.append(premise)
                        else:
                            premise_k = k - 1 if k > 1 else 1
                            new_premises.append(f"{premise}^{premise_k}")
                    
                    new_rules.append({
                        'name': f"{rule['name']}_k{k}",
                        'conclusion': new_conclusion,
                        'premises': new_premises
                    })
        
        # Étape 3: Ajouter les règles de propagation
        for literal in L_minus_A:
            for k in range(2, k_max + 1):
                new_rules.append({
                    'name': f"prop_{literal}_{k}",
                    'conclusion': f"{literal}^{k}",
                    'premises': [f"{literal}^{k-1}"]
                })
        
        non_circular_aba.rules = new_rules
        
        # Étape 4: Mettre à jour les contraires
        for assumption, contrary in self.contraries.items():
            if contrary in L_minus_A:
                for k in range(1, k_max + 1):
                    non_circular_aba.contraries[assumption] = f"{contrary}^{k}"
            else:
                non_circular_aba.contraries[assumption] = contrary
        
        print(f"Transformation terminée. {k_max} nouvelles versions créées.")
        return non_circular_aba

def parse_aba_input(aba_text):
    language = set()
    assumptions = set()
    contraries = {}
    rules = []
    preferences = []
    
    lines = aba_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('L:'):
            items = line[2:].strip(' []').split(',')
            language = set(item.strip() for item in items)
            
        elif line.startswith('A:'):
            items = line[2:].strip(' []').split(',')
            assumptions = set(item.strip() for item in items)
            
        elif line.startswith('C('):
            parts = line.split(':')
            assumption = parts[0][2:-1].strip()
            contrary = parts[1].strip()
            contraries[assumption] = contrary
            
        elif line.startswith('[') and ']:' in line:
            parts = line.split(']:')
            rule_name = parts[0][1:]
            rule_content = parts[1].strip()
            
            if '<-' in rule_content:
                conclusion, premises = rule_content.split('<-')
                conclusion = conclusion.strip()
                premises = [p.strip() for p in premises.split(',') if p.strip()]
            else:
                conclusion = rule_content.strip()
                premises = []
                
            rules.append({
                'name': rule_name,
                'conclusion': conclusion,
                'premises': premises
            })
            
        elif line.startswith('PREF:'):
            pref_part = line[5:].strip()
            # Handle notation like "a,b > c"
            if '>' in pref_part:
                better_side, worse = pref_part.split('>')
                better_side = better_side.strip()
                worse = worse.strip()
                
                # Split better side by comma
                better_items = [item.strip() for item in better_side.split(',')]
                
                # Add preferences for all items on the better side
                for better in better_items:
                    preferences.append((better, worse))
    
    return ABAFramework(language, assumptions, contraries, rules, preferences)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    try:
        aba_text = request.json.get('aba_text', '')
        
        # Parse input
        aba_original = parse_aba_input(aba_text)
        
        # Convert to atomic
        aba_atomic = aba_original.convert_to_atomic()
        
        # Generate arguments
        arguments = aba_atomic.generate_arguments_optimized()
        
        # Compute attacks
        attacks = aba_atomic.compute_all_attacks(arguments)
        
        # Format response
        result = {
            'success': True,
            'arguments': [
                {
                    'id': i,
                    'conclusion': conc,
                    'support': list(supp)
                }
                for i, (conc, supp) in enumerate(arguments)
            ],
            'attacks': {
                'standard': len(attacks['standard']),
                'normal': len(attacks['normal']),
                'reverse': len(attacks['reverse']),
                'total_aba_plus': len(attacks['all_aba_plus'])
            },
            'attack_details': {
                'normal': [a['description'] for a in attacks['normal']],
                'reverse': [a['description'] for a in attacks['reverse']]
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
