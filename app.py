from flask import Flask, render_template, request, jsonify
import os
from itertools import product

# INITIALISATION DE FLASK EN PREMIER
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
        Remplace chaque littéral non-assomption dans le corps des règles
        par une nouvelle assomption s_d et ajoute une règle s_d <- s
        """
        atomic_aba = ABAFramework()
        
        # Étape 1: Créer le nouveau langage
        # On garde le langage original et on ajoute les nouvelles assomptions
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

    def is_circular(self):
        """
        Détermine si le cadre ABA contient des circularités dans les règles
        Retourne True si circulaire, False sinon
        """
        # Construire le graphe de dépendance entre les conclusions
        dependency_graph = {}
        
        # Initialiser le graphe avec tous les symboles du langage
        for symbol in self.language:
            dependency_graph[symbol] = set()
        
        # Ajouter les dépendances basées sur les règles
        for rule in self.rules:
            conclusion = rule['conclusion']
            premises = rule['premises']
            
            for premise in premises:
                # Inclure TOUTES les prémisses, même les assomptions
                dependency_graph[conclusion].add(premise)
        
        # Vérifier tous les cycles avec un algorithme complet
        def find_all_cycles():
            cycles = []
            visited = set()
            
            def dfs(node, path, path_set):
                if node in path_set:
                    # Cycle détecté !
                    cycle_start = path.index(node)
                    cycle = path[cycle_start:]
                    # Vérifier si c'est un nouveau cycle
                    cycle_tuple = tuple(sorted(cycle))
                    if cycle_tuple not in cycles:
                        cycles.append(cycle_tuple)
                    return
                
                if node in visited:
                    return
                
                visited.add(node)
                path.append(node)
                path_set.add(node)
                
                for neighbor in dependency_graph[node]:
                    dfs(neighbor, path, path_set)
                
                path.pop()
                path_set.remove(node)
            
            # Pour chaque nœud, lancer une recherche DFS complète
            for node in sorted(dependency_graph.keys()):
                if node not in visited:
                    dfs(node, [], set())
            
            return cycles
        
        cycles = find_all_cycles()
        
        if cycles:
            return True
        else:
            return False
    
    def get_circular_dependencies(self):
        """
        Retourne toutes les circularités détectées dans le cadre ABA
        Version corrigée pour trouver tous les cycles
        """
        # Construire le graphe de dépendance
        dependency_graph = {}
        for symbol in self.language:
            dependency_graph[symbol] = set()
        
        for rule in self.rules:
            conclusion = rule['conclusion']
            premises = rule['premises']
            
            for premise in premises:
                # Inclure toutes les prémisses
                dependency_graph[conclusion].add(premise)
        
        # Fonction pour trouver tous les cycles
        def find_all_cycles():
            cycles = []
            visited = set()
            
            def dfs(node, path, path_set):
                if node in path_set:
                    # Cycle détecté
                    cycle_start = path.index(node)
                    cycle = path[cycle_start:]
                    # Vérifier si c'est un cycle valide (pas un doublon)
                    if len(cycle) >= 2:
                        cycle_tuple = tuple(sorted(cycle))
                        if cycle_tuple not in cycles:
                            cycles.append(cycle_tuple)
                    return
                
                if node in visited:
                    return
                
                visited.add(node)
                path.append(node)
                path_set.add(node)
                
                for neighbor in dependency_graph[node]:
                    dfs(neighbor, path, path_set)
                
                path.pop()
                path_set.remove(node)
            
            for node in sorted(dependency_graph.keys()):
                if node not in visited:
                    dfs(node, [], set())
            
            return [list(cycle) for cycle in cycles]
        
        cycles = find_all_cycles()
        
        return cycles

    def convert_to_non_circular(self):
        """
        Transforme un ABA circulaire en ABA non-circulaire selon la définition exacte
        """
        # Étape 1: Calculer k = |L \ A|
        non_assumption_language = self.language - self.assumptions
        k = len(non_assumption_language)
        
        # Étape 2: Créer les nouveaux éléments de langage
        new_language = set(self.language)  # L° = L ∪ {s^j}
        new_assumptions = set(self.assumptions)
        new_contraries = self.contraries.copy()
        new_rules = []
        
        # Dictionnaire pour mapper les symboles à leurs nouvelles versions
        symbol_mapping = {}
        
        # Créer des symboles distincts pour TOUTES les versions s^j, y compris s^1
        for s in self.language:
            for j in range(1, k + 1):
                new_symbol = f"{s}_{j}"  # Toujours créer s_1, s_2, s_3, etc.
                symbol_mapping[(s, j)] = new_symbol
                new_language.add(new_symbol)
                
                # Les nouvelles versions s^j deviennent des assomptions si s ∉ A
                if s in non_assumption_language:
                    new_assumptions.add(new_symbol)
                    if s in self.contraries:
                        new_contraries[new_symbol] = self.contraries[s]
        
        # Étape 3: Traiter les règles
        rule_counter = 0
        
        for rule in self.rules:
            s = rule['conclusion']
            premises = rule['premises']
            
            if not premises:  # Règle atomique
                # Créer k versions s^j ← pour j=1 à k
                for j in range(1, k + 1):
                    new_conclusion = symbol_mapping[(s, j)]
                    new_rules.append({
                        'name': f"r_{rule_counter}",
                        'conclusion': new_conclusion,
                        'premises': []
                    })
                    rule_counter += 1
                        
            else:  # Règle non-atomique
                # Créer k-1 versions s^j ← p'^1, ..., p'^n pour j=2 à k
                for j in range(2, k + 1):
                    new_conclusion = symbol_mapping[(s, j)]
                    new_premises = []
                    
                    for p in premises:
                        if p in self.assumptions:
                            # p' = p (garder l'assomption originale)
                            new_premises.append(p)
                        else:
                            # p' = p^{j-1}
                            new_premise = symbol_mapping[(p, j-1)]
                            new_premises.append(new_premise)
                    
                    new_rules.append({
                        'name': f"r_{rule_counter}",
                        'conclusion': new_conclusion,
                        'premises': new_premises
                    })
                    rule_counter += 1
        
        # Étape 4: Créer le nouveau cadre ABA non-circulaire
        non_circular_aba = ABAFramework()
        non_circular_aba.language = new_language
        non_circular_aba.assumptions = new_assumptions
        non_circular_aba.contraries = new_contraries
        non_circular_aba.rules = new_rules
        non_circular_aba.preferences = self.preferences.copy()
        
        return non_circular_aba

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
        premise_args = [args_by_conclusion[p] for p in premises]
        combinations = []
        
        for combo in product(*premise_args):
            combinations.append(list(combo))
        
        return combinations

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
            rule_name = parts[0][1:].strip()
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
            if '>' in pref_part:
                better, worse = pref_part.split('>')
                preferences.append((better.strip(), worse.strip()))
    
    return ABAFramework(language, assumptions, contraries, rules, preferences)

# ROUTES FLASK

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    try:
        aba_text = request.json.get('aba_text', '')
        
        # Parse input
        aba_original = parse_aba_input(aba_text)
        
        # Check circularity
        is_circular = aba_original.is_circular()
        circular_dependencies = aba_original.get_circular_dependencies() if is_circular else []
        
        # Apply atomic conversion if not circular
        if not is_circular:
            aba_atomic = aba_original.convert_to_atomic()
            
            # Generate arguments
            arguments = aba_atomic.generate_arguments_optimized()
            
            # Compute attacks
            attacks = aba_atomic.compute_all_attacks(arguments)
            
            # Format atomic framework info
            atomic_framework = {
                'language': list(aba_atomic.language),
                'assumptions': list(aba_atomic.assumptions),
                'contraries': aba_atomic.contraries,
                'rules_count': len(aba_atomic.rules),
                'rules': [{
                    'name': rule['name'],
                    'conclusion': rule['conclusion'],
                    'premises': rule['premises']
                } for rule in aba_atomic.rules]
            }
        else:
            # If circular, we can't generate arguments/attacks
            aba_atomic = None
            arguments = []
            attacks = {
                'standard': [],
                'normal': [],
                'reverse': [],
                'all_aba_plus': []
            }
            atomic_framework = None
        
        # Format response
        result = {
            'success': True,
            'is_circular': is_circular,
            'circular_dependencies': circular_dependencies,
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
                'standard': [{'description': a['description'], 'from': a['from'], 'to': a['to']} for a in attacks['standard']],
                'normal': [{'description': a['description'], 'from': a['from'], 'to': a['to']} for a in attacks['normal']],
                'reverse': [{'description': a['description'], 'from': a['from'], 'to': a['to']} for a in attacks['reverse']]
            },
            'framework_info': {
                'original_language': list(aba_original.language),
                'original_assumptions': list(aba_original.assumptions),
                'original_contraries': aba_original.contraries,
                'preferences': aba_original.preferences,
                'original_rules': [{
                    'name': rule['name'],
                    'conclusion': rule['conclusion'],
                    'premises': rule['premises']
                } for rule in aba_original.rules]
            },
            'atomic_framework': atomic_framework
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/transform_non_circular', methods=['POST'])
def transform_non_circular():
    try:
        aba_text = request.json.get('aba_text', '')
        
        # Parse input
        aba_original = parse_aba_input(aba_text)
        
        # Apply non-circular transformation
        aba_transformed = aba_original.convert_to_non_circular()
        
        # Apply atomic conversion to transformed framework
        aba_atomic = aba_transformed.convert_to_atomic()
        
        # Generate arguments
        arguments = aba_atomic.generate_arguments_optimized()
        
        # Compute attacks
        attacks = aba_atomic.compute_all_attacks(arguments)
        
        # Format transformation info
        non_assumption_language = aba_original.language - aba_original.assumptions
        k_value = len(non_assumption_language)
        
        transformation_info = {
            'k_value': k_value,
            'non_assumptions': list(non_assumption_language),
            'original_language_size': len(aba_original.language),
            'transformed_language_size': len(aba_transformed.language),
            'original_rules_count': len(aba_original.rules),
            'transformed_rules_count': len(aba_transformed.rules),
            'original_assumptions': list(aba_original.assumptions),
            'transformed_assumptions': list(aba_transformed.assumptions),
            'original_rules': [{
                'name': rule['name'],
                'conclusion': rule['conclusion'],
                'premises': rule['premises']
            } for rule in aba_original.rules],
            'transformed_rules': [{
                'name': rule['name'],
                'conclusion': rule['conclusion'],
                'premises': rule['premises']
            } for rule in aba_transformed.rules]
        }
        
        # Format atomic framework info
        atomic_framework = {
            'language': list(aba_atomic.language),
            'assumptions': list(aba_atomic.assumptions),
            'contraries': aba_atomic.contraries,
            'rules_count': len(aba_atomic.rules),
            'rules': [{
                'name': rule['name'],
                'conclusion': rule['conclusion'],
                'premises': rule['premises']
            } for rule in aba_atomic.rules]
        }
        
        # Format response
        result = {
            'success': True,
            'transformation_type': 'non_circular',
            'is_circular': False,  # After transformation, it's no longer circular
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
                'standard': [{'description': a['description'], 'from': a['from'], 'to': a['to']} for a in attacks['standard']],
                'normal': [{'description': a['description'], 'from': a['from'], 'to': a['to']} for a in attacks['normal']],
                'reverse': [{'description': a['description'], 'from': a['from'], 'to': a['to']} for a in attacks['reverse']]
            },
            'framework_info': {
                'original_language': list(aba_original.language),
                'original_assumptions': list(aba_original.assumptions),
                'original_contraries': aba_original.contraries,
                'preferences': aba_original.preferences,
                'original_rules': [{
                    'name': rule['name'],
                    'conclusion': rule['conclusion'],
                    'premises': rule['premises']
                } for rule in aba_original.rules]
            },
            'atomic_framework': atomic_framework,
            'transformation_info': transformation_info
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/transform_atomic', methods=['POST'])
def transform_atomic():
    try:
        aba_text = request.json.get('aba_text', '')
        
        # Parse input
        aba_original = parse_aba_input(aba_text)
        
        # Apply atomic conversion directly (even if circular)
        aba_atomic = aba_original.convert_to_atomic()
        
        # Generate arguments
        arguments = aba_atomic.generate_arguments_optimized()
        
        # Compute attacks
        attacks = aba_atomic.compute_all_attacks(arguments)
        
        # Format transformation info for atomic conversion
        transformation_info = {
            'transformation_type': 'atomic',
            'original_language_size': len(aba_original.language),
            'atomic_language_size': len(aba_atomic.language),
            'original_assumptions_count': len(aba_original.assumptions),
            'atomic_assumptions_count': len(aba_atomic.assumptions),
            'original_rules_count': len(aba_original.rules),
            'atomic_rules_count': len(aba_atomic.rules),
            'new_assumptions': list(aba_atomic.assumptions - aba_original.assumptions)
        }
        
        # Format atomic framework info
        atomic_framework = {
            'language': list(aba_atomic.language),
            'assumptions': list(aba_atomic.assumptions),
            'contraries': aba_atomic.contraries,
            'rules_count': len(aba_atomic.rules),
            'rules': [{
                'name': rule['name'],
                'conclusion': rule['conclusion'],
                'premises': rule['premises']
            } for rule in aba_atomic.rules]
        }
        
        # Format response
        result = {
            'success': True,
            'transformation_type': 'atomic',
            'is_circular': aba_original.is_circular(),  # Keep original circularity status
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
                'standard': [{'description': a['description'], 'from': a['from'], 'to': a['to']} for a in attacks['standard']],
                'normal': [{'description': a['description'], 'from': a['from'], 'to': a['to']} for a in attacks['normal']],
                'reverse': [{'description': a['description'], 'from': a['from'], 'to': a['to']} for a in attacks['reverse']]
            },
            'framework_info': {
                'original_language': list(aba_original.language),
                'original_assumptions': list(aba_original.assumptions),
                'original_contraries': aba_original.contraries,
                'preferences': aba_original.preferences,
                'original_rules': [{
                    'name': rule['name'],
                    'conclusion': rule['conclusion'],
                    'premises': rule['premises']
                } for rule in aba_original.rules]
            },
            'atomic_framework': atomic_framework,
            'transformation_info': transformation_info
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

# CE DOIT ÊTRE LA DERNIÈRE LIGNE
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)