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
        """
        Convertit le cadre ABA en version atomique sensible
        """
        atomic_aba = ABAFramework()
        
        # Étape 1: Créer le nouveau langage
        new_language = set(self.language)
        new_assumptions = set(self.assumptions)
        
        # Dictionnaire pour mapper les littéraux non-assomptions vers leurs nouvelles assomptions
        literal_to_new_assumption = {}
        new_rules = []
        
        # Étape 2: Identifier tous les littéraux non-assomptions qui apparaissent dans les corps de règles
        non_assumption_literals_in_bodies = set()
        
        for rule in self.rules:
            for premise in rule['premises']:
                if premise not in self.assumptions:
                    non_assumption_literals_in_bodies.add(premise)
        
        # Étape 3: Créer de nouvelles assomptions pour chaque littéral non-assomption
        for literal in non_assumption_literals_in_bodies:
            new_assumption_d = f"{literal}_d"  # _d pour "dérivé"
            literal_to_new_assumption[literal] = new_assumption_d
            new_language.add(new_assumption_d)
            new_assumptions.add(new_assumption_d)

            new_assumption_nd = f"{literal}_nd"  # _nd pour "non-dérivé"
            new_language.add(new_assumption_nd)
            new_assumptions.add(new_assumption_nd)
            
        # Étape 4: Transformer les règles originales
        for rule in self.rules:
            new_premises = []
            
            for premise in rule['premises']:
                if premise in self.assumptions:
                    # Garder les assomptions originales
                    new_premises.append(premise)
                else:
                    # Remplacer les littéraux non-assomptions par leurs nouvelles assomptions
                    new_premises.append(literal_to_new_assumption[premise])
            
            new_rules.append({
                'name': f"atom_{rule['name']}",
                'conclusion': rule['conclusion'],
                'premises': new_premises
            })
        
        # Étape 5: Mettre à jour les contraires
        new_contraries = self.contraries.copy()
        for literal in non_assumption_literals_in_bodies:
            new_assumption_d = f"{literal}_d"
            new_assumption_nd = f"{literal}_nd"
            
            # Contraire de _d est _nd
            new_contraries[new_assumption_d] = new_assumption_nd
            # Contraire de _nd est le littéral original
            new_contraries[new_assumption_nd] = literal
            
        # Étape 6: Construire le nouveau cadre atomique
        atomic_aba.language = new_language
        atomic_aba.assumptions = new_assumptions
        atomic_aba.contraries = new_contraries
        atomic_aba.rules = new_rules
        atomic_aba.preferences = self.preferences.copy()
        
        return atomic_aba

    def get_contrary(self, assumption):
        """
        Retourne le contraire d'une assomption
        """
        return self.contraries.get(assumption)
    
    def add_preference(self, better, worse):
        """
        Ajoute une préférence: better > worse
        """
        if better not in self.assumptions or worse not in self.assumptions:
            raise ValueError("Les préférences ne peuvent être définies que entre assomptions")
        
        self.preferences.append((better, worse))
    
    def get_preference_relation(self, assumption1, assumption2):
        """
        Retourne la relation de préférence entre deux assomptions
        Retourne: 1 si assumption1 > assumption2, -1 si assumption2 > assumption1, 0 sinon
        """
        if (assumption1, assumption2) in self.preferences:
            return 1
        elif (assumption2, assumption1) in self.preferences:
            return -1
        else:
            return 0

    def generate_arguments_optimized(self, max_iterations=100):
        """
        Version optimisée avec limite d'itérations pour éviter les boucles infinies
        """
        arguments = []
        
        # Arguments de base : chaque assomption est un argument pour elle-même
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
                
                # Vérifier si on peut appliquer la règle
                valid_combinations = self._find_valid_combinations(premises, current_args)
                
                for support_args in valid_combinations:
                    # Calculer le support complet
                    full_support = set()
                    for arg in support_args:
                        full_support.update(arg[1])
                    
                    new_arg = (conclusion, frozenset(full_support))
                    
                    if new_arg not in arguments:
                        arguments.append(new_arg)
                        changed = True
        
        return arguments

    def _find_valid_combinations(self, premises, arguments):
        """
        Trouve les combinaisons valides d'arguments qui satisfont toutes les prémisses
        """
        if not premises:
            return [[]]  # Une combinaison vide pour les règles sans prémisses
        
        # Grouper les arguments par conclusion
        args_by_conclusion = {}
        for arg in arguments:
            if arg[0] not in args_by_conclusion:
                args_by_conclusion[arg[0]] = []
            args_by_conclusion[arg[0]].append(arg)
        
        # Vérifier que toutes les prémisses peuvent être satisfaites
        for premise in premises:
            if premise not in args_by_conclusion:
                return []  # Impossible de satisfaire cette prémisse
        
        # Générer toutes les combinaisons possibles
        from itertools import product
        
        premise_args = [args_by_conclusion[p] for p in premises]
        combinations = []
        
        for combo in product(*premise_args):
            combinations.append(list(combo))
        
        return combinations

    def compute_standard_attacks(self, arguments):
        """
        Calcule les attaques standard ABA (sans préférences)
        """
        attacks = []
        
        for i, (conc1, supp1) in enumerate(arguments):
            for j, (conc2, supp2) in enumerate(arguments):
                if i == j:
                    continue  # Un argument n'attaque pas lui-même
                    
                # Vérifier chaque assomption dans le support de l'argument cible
                for assumption in supp2:
                    contrary = self.get_contrary(assumption)
                    if contrary == conc1:
                        attacks.append({
                            'type': 'standard',
                            'from': i,
                            'to': j,
                            'via_assumption': assumption,
                            'description': f"Argument {i} ({conc1}) attaque Argument {j} via l'assomption '{assumption}'"
                        })
        
        return attacks

    def compute_normal_attacks(self, arguments, standard_attacks):
        """
        Calcule les attaques NORMALES ABA+
        """
        normal_attacks = []
        
        for attack in standard_attacks:
            attacker_idx = attack['from']
            target_idx = attack['to']
            target_assumption = attack['via_assumption']
            
            attacker_arg = arguments[attacker_idx]
            _, attacker_support = attacker_arg
            
            # Vérifier si l'attaque est valide selon les préférences
            attack_valid = True
            
            for assump in attacker_support:
                # Si une assomption de l'attaquant est strictement moins préférée que la cible
                if self.get_preference_relation(assump, target_assumption) == -1:
                    attack_valid = False
                    break
            
            if attack_valid:
                normal_attacks.append({
                    'type': 'normal',
                    'from': attacker_idx,
                    'to': target_idx,
                    'via_assumption': target_assumption,
                    'description': f"Attaque NORMALE: Argument {attacker_idx} → Argument {target_idx} (via '{target_assumption}')"
                })
        
        return normal_attacks

    def compute_reverse_attacks(self, arguments):
        """
        Calcule les attaques INVERSES selon la définition stricte ABA+
        """
        reverse_attacks = []
        
        for i, (conc_i, supp_i) in enumerate(arguments):  # X = supp_i
            for j, (conc_j, supp_j) in enumerate(arguments):  # Y = supp_j
                if i == j:
                    continue
                    
                # Vérifier si Y (argument j) a un argument qui attaque X (argument i)
                for x in supp_i:  # x ∈ X
                    contrary_x = self.get_contrary(x)
                    if contrary_x and contrary_x == conc_j:  # Y conclut ¯x
                        # Maintenant vérifier la condition de préférence faible
                        for y_prime in supp_j:  # y' ∈ Y' ⊆ Y
                            if self.get_preference_relation(y_prime, x) == -1:  # y' < x
                                reverse_attacks.append({
                                    'type': 'reverse',
                                    'from': i,  # X attaque Y
                                    'to': j,    # Y est attaqué
                                    'target_assumption': x,  # L'assomption ciblée dans X
                                    'weak_assumption': y_prime,  # L'assomption faible dans Y
                                    'description': f"Attaque INVERSE: Argument {i} (X) → Argument {j} (Y) - Y attaque X via '{conc_j}'=C('{x}') mais y'='{y_prime}' < x='{x}'"
                                })
                                break  # Une seule assomption faible suffit
        
        return reverse_attacks

    def compute_all_attacks(self, arguments):
        """
        Calcule tous les types d'attaques selon la définition stricte ABA+
        """
        # 1. Attaques standard (ABA simple) - pour référence
        standard_attacks = self.compute_standard_attacks(arguments)
        
        # 2. Attaques normales (ABA+)
        normal_attacks = self.compute_normal_attacks(arguments, standard_attacks)
        
        # 3. Attaques inverses (ABA+)
        reverse_attacks = self.compute_reverse_attacks(arguments)
        
        # Combiner toutes les attaques ABA+
        all_attacks = normal_attacks + reverse_attacks
        
        return {
            'standard': standard_attacks,
            'normal': normal_attacks, 
            'reverse': reverse_attacks,
            'all_aba_plus': all_attacks
        }

    def __str__(self):
        """Représentation textuelle du cadre ABA"""
        result = f"Langage: {self.language}\n"
        result += f"Assomptions: {self.assumptions}\n"
        result += f"Contraires: {self.contraries}\n"
        result += f"Préférences: {self.preferences}\n"
        result += "Règles:\n"
        for rule in self.rules:
            result += f"  {rule['name']}: {rule['conclusion']} <- {', '.join(rule['premises']) if rule['premises'] else '∅'}\n"
        return result

def parse_aba_input(aba_text):
    """
    Parse le format ABA et retourne un objet ABAFramework
    """
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
            },
            'framework_info': {
                'original_assumptions': list(aba_original.assumptions),
                'atomic_assumptions': list(aba_atomic.assumptions),
                'rules_count': len(aba_atomic.rules),
                'preferences': aba_atomic.preferences
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