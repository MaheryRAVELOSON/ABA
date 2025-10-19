@app.route('/process', methods=['POST'])
def process():
    try:
        aba_text = request.json.get('aba_text', '')
        
        # Parse input
        aba_original = parse_aba_input(aba_text)
        
        # Debug info
        debug_info = {
            'original_framework': str(aba_original),
            'conversion_steps': []
        }
        
        # Convert to atomic with detailed steps
        debug_info['conversion_steps'].append("=== DÉBUT DE LA CONVERSION ATOMIQUE ===")
        
        atomic_aba = ABAFramework()
        new_language = set(aba_original.language)
        new_assumptions = set(aba_original.assumptions)
        literal_to_new_assumption = {}
        new_rules = []
        
        # Identify non-assumption literals in rule bodies
        non_assumption_literals_in_bodies = set()
        for rule in aba_original.rules:
            for premise in rule['premises']:
                if premise not in aba_original.assumptions:
                    non_assumption_literals_in_bodies.add(premise)
        
        debug_info['conversion_steps'].append(f"Littéraux non-assomptions dans les corps de règles: {list(non_assumption_literals_in_bodies)}")
        
        # Create new assumptions for each non-assumption literal
        for literal in non_assumption_literals_in_bodies:
            new_assumption_d = f"{literal}_d"
            new_assumption_nd = f"{literal}_nd"
            
            literal_to_new_assumption[literal] = new_assumption_d
            new_language.add(new_assumption_d)
            new_language.add(new_assumption_nd)
            new_assumptions.add(new_assumption_d)
            new_assumptions.add(new_assumption_nd)
            
            debug_info['conversion_steps'].append(f"Création assomptions pour '{literal}': '{new_assumption_d}' et '{new_assumption_nd}'")
        
        # Transform original rules
        for rule in aba_original.rules:
            new_premises = []
            for premise in rule['premises']:
                if premise in aba_original.assumptions:
                    new_premises.append(premise)
                else:
                    new_premises.append(literal_to_new_assumption[premise])
            
            new_rules.append({
                'name': f"atom_{rule['name']}",
                'conclusion': rule['conclusion'],
                'premises': new_premises
            })
            
            debug_info['conversion_steps'].append(f"Règle transformée: {rule['name']} -> atom_{rule['name']}")
            debug_info['conversion_steps'].append(f"  Originale: {rule['conclusion']} <- {rule['premises']}")
            debug_info['conversion_steps'].append(f"  Atomique: {rule['conclusion']} <- {new_premises}")
        
        # Update contraries
        new_contraries = aba_original.contraries.copy()
        for literal in non_assumption_literals_in_bodies:
            new_assumption_d = f"{literal}_d"
            new_assumption_nd = f"{literal}_nd"
            
            new_contraries[new_assumption_d] = new_assumption_nd
            new_contraries[new_assumption_nd] = literal
            
            debug_info['conversion_steps'].append(f"Contraires définis: C({new_assumption_d}) = {new_assumption_nd}, C({new_assumption_nd}) = {literal}")
        
        # Build atomic framework
        atomic_aba.language = new_language
        atomic_aba.assumptions = new_assumptions
        atomic_aba.contraries = new_contraries
        atomic_aba.rules = new_rules
        atomic_aba.preferences = aba_original.preferences.copy()
        
        debug_info['conversion_steps'].append("=== CONVERSION ATOMIQUE TERMINÉE ===")
        
        # Generate arguments with detailed steps
        debug_info['argument_generation'] = []
        arguments = []
        
        # Base arguments (assumptions)
        for assumption in atomic_aba.assumptions:
            arguments.append((assumption, {assumption}))
            debug_info['argument_generation'].append(f"Argument de base: ({assumption}, {{{assumption}}})")
        
        # Iterative generation
        iteration = 0
        changed = True
        max_iterations = 100
        
        while changed and iteration < max_iterations:
            changed = False
            iteration += 1
            debug_info['argument_generation'].append(f"--- Itération {iteration} ---")
            
            current_args = arguments.copy()
            
            for rule in atomic_aba.rules:
                conclusion = rule['conclusion']
                premises = rule['premises']
                
                valid_combinations = atomic_aba._find_valid_combinations(premises, current_args)
                
                for support_args in valid_combinations:
                    full_support = set()
                    for arg in support_args:
                        full_support.update(arg[1])
                    
                    new_arg = (conclusion, frozenset(full_support))
                    
                    if new_arg not in arguments:
                        arguments.append(new_arg)
                        changed = True
                        debug_info['argument_generation'].append(f"Nouvel argument: ({conclusion}, {set(full_support)})")
                        debug_info['argument_generation'].append(f"  Règle appliquée: {rule['name']}: {conclusion} <- {premises}")
                        debug_info['argument_generation'].append(f"  Support combiné: {[f'({a[0]}, {set(a[1])})' for a in support_args]}")
        
        debug_info['argument_generation'].append(f"=== GÉNÉRATION TERMINÉE: {len(arguments)} arguments ===")
        
        # Compute attacks with detailed steps
        debug_info['attack_computation'] = []
        attacks = atomic_aba.compute_all_attacks(arguments)
        
        # Add detailed attack computation
        debug_info['attack_computation'].append("=== CALCUL DES ATTAQUES ===")
        
        # Standard attacks
        debug_info['attack_computation'].append("Attaques standard:")
        for attack in attacks['standard']:
            from_arg = arguments[attack['from']]
            to_arg = arguments[attack['to']]
            debug_info['attack_computation'].append(
                f"  {attack['description']}\n"
                f"    Attaquant: {from_arg}\n"
                f"    Cible: {to_arg}"
            )
        
        # Normal attacks
        debug_info['attack_computation'].append("Attaques normales (ABA+):")
        for attack in attacks['normal']:
            from_arg = arguments[attack['from']]
            to_arg = arguments[attack['to']]
            debug_info['attack_computation'].append(
                f"  {attack['description']}\n"
                f"    Attaquant: {from_arg}\n"
                f"    Cible: {to_arg}\n"
                f"    Vérification préférences: OK"
            )
        
        # Reverse attacks
        debug_info['attack_computation'].append("Attaques inverses (ABA+):")
        for attack in attacks['reverse']:
            from_arg = arguments[attack['from']]
            to_arg = arguments[attack['to']]
            debug_info['attack_computation'].append(
                f"  {attack['description']}\n"
                f"    X: {from_arg}\n"
                f"    Y: {to_arg}\n"
                f"    y' faible: {attack['weak_assumption']} < {attack['target_assumption']}"
            )
        
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
                'reverse': [a['description'] for a in attacks['reverse']],
                'standard': [a['description'] for a in attacks['standard']]
            },
            'framework_info': {
                'original_assumptions': list(aba_original.assumptions),
                'atomic_assumptions': list(atomic_aba.assumptions),
                'rules_count': len(atomic_aba.rules),
                'preferences': atomic_aba.preferences,
                'original_rules': aba_original.rules,
                'atomic_rules': atomic_aba.rules,
                'contraries': atomic_aba.contraries
            },
            'debug_info': debug_info
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400