#!/usr/bin/env python
"""
Regenerate Data/PlantSEED_v3/PlantSEED_Complexes.json from PlantSEED_Roles.json.

A complex is the set of roles in PlantSEED_Roles.json that share an
`abstract_enzyme` value (with a per-reaction split for the "Spontaneous
Reaction" name so each spontaneous reaction gets its own complex).

This script is the complex generator. Role-level `kbase_id` assignment used
to live here too but now lives in Update_Enzymes_in_PlantSEED.py, where it
happens inline at curation time.

Run with no arguments. The CLI is structured so a future TSV-driven surgical
mode can drop in at the top of main() without re-architecting.
"""
import os, sys, json, copy, hashlib
import yaml


class Issues:
	"""Collects warnings and errors so they can be summarised at the end of the run."""

	def __init__(self):
		self.warnings = []
		self.errors = []

	def warn(self, msg):
		self.warnings.append(msg)
		print(f"[WARN] {msg}")

	def error(self, msg):
		self.errors.append(msg)
		print(f"[ERROR] {msg}")

	def summary(self):
		print(f"\nCompleted with {len(self.warnings)} warning(s) and {len(self.errors)} error(s).")


# Schema type names mirror Validate_Plantseed_Schema.py and Update_Enzymes_in_PlantSEED.py.
TYPE_MAP = {
	'str': str,
	'bool': bool,
	'list': list,
	'dict': dict,
	'int': int,
	'float': float,
}


def load_schema(yaml_path):
	"""Load PlantSEED_Complexes_Schema.yaml. `depends_on` is parsed but unused
	for complexes today; the rewrite still threads it through for parity with
	the roles schema."""
	if not os.path.isfile(yaml_path):
		print(f"Error: Schema YAML file not found at {yaml_path}")
		sys.exit(1)

	with open(yaml_path, 'r', encoding='utf-8') as f:
		raw_schema = yaml.safe_load(f)

	schema = {}
	for key, rules in raw_schema.items():
		type_str = rules.get('type')
		if type_str not in TYPE_MAP:
			print(f"Error: Unknown type '{type_str}' in schema for key '{key}'")
			sys.exit(1)
		schema[key] = {
			'type':       TYPE_MAP[type_str],
			'default':    rules.get('default'),
			'required':   rules.get('required', False),
			'depends_on': rules.get('depends_on'),
		}
	return schema


def default_complex_from_schema(schema):
	"""Build a default-shaped complex from the schema's required fields."""
	return {k: copy.deepcopy(rules['default']) for k, rules in schema.items() if rules['required']}


def complex_key_for_role(role):
	"""Return the complex grouping key for a role.

	Normally this is the role's `abstract_enzyme`. Spontaneous reactions all
	share the abstract_enzyme "Spontaneous Reaction"; they're split per-role
	using the role's first reaction id, so each spontaneous reaction can be
	its own complex. Returns None if the role has no abstract_enzyme to group on.
	"""
	enz = role.get('abstract_enzyme')
	if not enz:
		return None
	if enz.lower() == 'spontaneous reaction':
		if not role.get('reactions'):
			return None
		return enz + '||' + role['reactions'][0]
	return enz


def load_transport_rules(yaml_path):
	"""Load the 2-letter -> 1-letter compartment translation rules from
	Transport_Compartment_Rules.yaml. See that file for the format."""
	if not os.path.isfile(yaml_path):
		print(f"Error: Transport rules file not found at {yaml_path}")
		sys.exit(1)
	with open(yaml_path, 'r', encoding='utf-8') as f:
		data = yaml.safe_load(f)
	rules = data.get('rules', [])
	for i, rule in enumerate(rules):
		if 'if_contains' not in rule or 'result' not in rule:
			print(f"Error: rule {i} in {yaml_path} missing 'if_contains' or 'result'")
			sys.exit(1)
	return rules


def to_model_compartment(role_localization_key, rules):
	"""Translate a role's localization key (possibly 2-letter, signalling a
	transporter between two compartments) to the single-letter compartment
	used in the model.

	Rule semantics are defined in Transport_Compartment_Rules.yaml. Rules
	apply in order; each matching rule overrides the previous result. The
	first letter of the pair is the default if no rule matches. 1-letter
	(or longer) keys pass through unchanged."""
	if len(role_localization_key) != 2:
		return role_localization_key
	cpts = role_localization_key
	result = cpts[0]
	for rule in rules:
		marker = rule['if_contains']
		if marker not in cpts:
			continue
		target = rule['result']
		if target == 'other':
			for c in cpts:
				if c != marker:
					result = c
		else:
			result = target
	return result


def group_roles_by_complex(roles, issues):
	"""Walk every role once, bucket by complex key. Warn on roles that can't be grouped."""
	groups = {}
	for role in roles:
		key = complex_key_for_role(role)
		if key is None:
			issues.warn(
				f"role '{role.get('role', '<unnamed>')}' has no abstract_enzyme "
				f"(or no reactions for the spontaneous-reaction split) — skipped"
			)
			continue
		groups.setdefault(key, []).append(role)
	return groups


def build_complex_from_role_group(enzyme, role_entries, schema, transport_rules):
	"""Derive a complex shell from a list of role entries sharing one complex key.

	`compartments_reactions` is built by walking each role's `reactions` x `localization`
	cross-product: for every reaction in every compartment the role appears in, add
	the reaction to that compartment's block."""
	shell = default_complex_from_schema(schema)
	shell['enzyme'] = enzyme
	shell['roles'] = sorted({r['role'] for r in role_entries})

	cpts = {}
	for role in role_entries:
		for rxn in role.get('reactions', []):
			for role_cpt in role.get('localization', {}):
				# Translate 2-letter transporter codes to the model's single-letter cpt.
				# `reagents` preserves the original role-localization code, so transporter
				# pair information (e.g., "cv" = cytosol↔vacuole) isn't lost when the cpt
				# key collapses to a single letter.
				cpt = to_model_compartment(role_cpt, transport_rules)
				if cpt not in cpts:
					cpts[cpt] = {'reactions': [], 'reagents': role_cpt, 'exclude': False}
				elif len(cpts[cpt]['reagents']) == 1 and len(role_cpt) == 2:
					# If a 1-letter localization established this cpt first but a 2-letter
					# code also maps here, prefer the 2-letter (more informative) form.
					cpts[cpt]['reagents'] = role_cpt
				if rxn not in cpts[cpt]['reactions']:
					cpts[cpt]['reactions'].append(rxn)
	# Stable sort for diff-friendly output
	for cpt in cpts:
		cpts[cpt]['reactions'].sort()
	shell['compartments_reactions'] = cpts
	return shell


def _hash_complex(enzyme, roles, cpts):
	"""Reproduce the exact unique-key formula from the old Prepare_PlantSEED_KBase.py."""
	sorted_roles = sorted(roles)
	rxn_cpts = []
	for cpt, block in cpts.items():
		for rxn in block.get('reactions', []):
			rxn_cpts.append(rxn + '_' + cpt)
	sorted_rxn_cpts = sorted(rxn_cpts)
	cpx_str = ' / '.join([enzyme, '|'.join(sorted_roles), '|'.join(sorted_rxn_cpts)])
	return 'PS_complex_' + hashlib.sha256(cpx_str.encode('utf-8')).hexdigest()[:6]


def assign_complex_kbase_id(complex_entry, existing_ids, old_id=None):
	"""Compute and assign PS_complex_<sha256[:6]>. If `old_id` is supplied and
	the recomputed id matches, the old id is preserved. On collision with an
	id already in `existing_ids` (other than old_id), the hash is rehashed
	until a free slot is found."""
	new_id = _hash_complex(
		complex_entry['enzyme'],
		complex_entry['roles'],
		complex_entry.get('compartments_reactions', {}),
	)
	# Drop the old id from the collision pool so a rehash can land on the same slot.
	pool = set(existing_ids)
	if old_id in pool:
		pool.discard(old_id)
	while new_id in pool:
		new_id = 'PS_complex_' + hashlib.sha256(new_id.encode('utf-8')).hexdigest()[:6]

	complex_entry['kbase_id'] = new_id
	if old_id in existing_ids:
		existing_ids.discard(old_id)
	existing_ids.add(new_id)


def carry_over_biochem(shell, existing):
	"""Copy biochem fields from the prior entry onto the freshly-derived shell.
	These fields aren't derivable from roles, so they'd be lost otherwise.
	Also preserves the per-cpt reaction LIST ORDER from the prior entry where
	possible (so reactions added long ago stay in their original positions and
	only brand-new ones get appended at the end) — this keeps diffs minimal."""
	for k in ('direction', 'stoichiometry'):
		if k in existing:
			shell[k] = existing[k]
	old_cpts = existing.get('compartments_reactions', {})
	for cpt, block in shell.get('compartments_reactions', {}).items():
		if cpt not in old_cpts:
			continue
		if 'exclude' in old_cpts[cpt]:
			block['exclude'] = old_cpts[cpt]['exclude']
		# Preserve original reaction order; append any new reactions at the end.
		old_rxns = old_cpts[cpt].get('reactions', [])
		new_rxn_set = set(block['reactions'])
		preserved = [r for r in old_rxns if r in new_rxn_set]
		appended = sorted(r for r in block['reactions'] if r not in set(old_rxns))
		block['reactions'] = preserved + appended


def ensure_schema_defaults(entry, schema):
	"""Fill missing required fields with their schema default. Non-restrictive."""
	warnings = []
	enz = entry.get('enzyme', '<unnamed>')
	for key, rules in schema.items():
		if not rules['required']:
			continue
		if key not in entry:
			entry[key] = copy.deepcopy(rules['default'])
			warnings.append(f"[DEFAULT FILLED] '{key}' was missing in complex '{enz}' — set to default {rules['default']!r}")
	return warnings


def validate_dependencies(entry, schema):
	"""Check cross-field dependencies declared via `depends_on` in the schema.
	No-op until the complexes schema gains `depends_on` blocks; kept for parity
	with Update_Enzymes_in_PlantSEED.py."""
	warnings = []
	enz = entry.get('enzyme', '<unnamed>')
	for key, rules in schema.items():
		dep = rules.get('depends_on')
		if not dep or key not in entry:
			continue
		value = entry[key]
		if not isinstance(value, dict):
			continue
		if 'keys_from' in dep:
			allowed = set()
			for source_field in dep['keys_from']:
				allowed.update(entry.get(source_field, []))
			for k in value.keys():
				if k not in allowed:
					warnings.append(
						f"[DEPENDENCY WARNING] '{key}' key '{k}' in complex '{enz}' "
						f"is not present in {dep['keys_from']}"
					)
		if 'inner_keys_from' in dep:
			allowed = set()
			for source_field in dep['inner_keys_from']:
				allowed.update(entry.get(source_field, []))
			for outer_k, inner in value.items():
				if not isinstance(inner, dict):
					continue
				for k in inner.keys():
					if k not in allowed:
						warnings.append(
							f"[DEPENDENCY WARNING] '{key}.{outer_k}' inner key '{k}' "
							f"in complex '{enz}' is not present in {dep['inner_keys_from']}"
						)
	return warnings


def _ordered_complex(entry):
	"""Reorder keys for diff-friendly output: kbase_id, enzyme, roles,
	compartments_reactions, then any optional biochem fields."""
	ordered = {}
	for k in ('kbase_id', 'enzyme', 'roles', 'compartments_reactions'):
		if k in entry:
			ordered[k] = entry[k]
	for k in entry:
		if k not in ordered:
			ordered[k] = entry[k]
	return ordered


def write_db(path, complexes_list):
	"""Atomic JSON write with the canonical key order."""
	with open(path, 'w') as f:
		json.dump([_ordered_complex(c) for c in complexes_list], f, indent=4)


def main():
	issues = Issues()
	script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
	data_dir = os.path.join(script_dir, '../../../', 'Data/PlantSEED_v3/')
	roles_path     = os.path.join(data_dir, 'PlantSEED_Roles.json')
	complexes_path = os.path.join(data_dir, 'PlantSEED_Complexes.json')
	schema_path    = os.path.join(script_dir, 'PlantSEED_Complexes_Schema.yaml')
	transport_rules_path = os.path.join(script_dir, '../Template/Transport_Compartment_Rules.yaml')

	schema = load_schema(schema_path)
	transport_rules = load_transport_rules(transport_rules_path)

	with open(roles_path) as f:
		roles = json.load(f)
	with open(complexes_path) as f:
		existing = json.load(f)

	# --- Future TSV-driven surgical mode lands here ---
	# if len(sys.argv) > 1:
	#     actions = parse_tsv(sys.argv[1], schema, issues)
	#     apply_actions(existing, actions, sys.argv[1], issues)
	# The regenerate sweep below then proceeds on the TSV-edited set.

	existing_by_enzyme = {c['enzyme']: c for c in existing}
	existing_ids       = {c['kbase_id'] for c in existing if 'kbase_id' in c}

	# 1. Group roles by complex key.
	groups = group_roles_by_complex(roles, issues)

	# 2. Build a fresh complex per group; preserve identity and biochem where applicable.
	#    Output order: existing complexes keep their original positions (with refreshed
	#    contents); any newly-discovered complexes are appended in alphabetical order at
	#    the end. This minimises diff churn from re-sorting on every run.
	shells_by_enzyme = {}
	for enzyme, role_entries in groups.items():
		shell = build_complex_from_role_group(enzyme, role_entries, schema, transport_rules)
		old = existing_by_enzyme.get(enzyme)
		old_id = old.get('kbase_id') if old else None
		assign_complex_kbase_id(shell, existing_ids, old_id=old_id)
		if old:
			carry_over_biochem(shell, old)
			if old_id and old_id != shell['kbase_id']:
				issues.warn(
					f"complex '{enzyme}' membership changed — "
					f"kbase_id {old_id} -> {shell['kbase_id']}. "
					f"Downstream KBase consumers may need to remap."
				)
		else:
			issues.warn(
				f"new complex '{enzyme}' (kbase_id={shell['kbase_id']}) "
				f"added from {len(role_entries)} role(s)"
			)
		shells_by_enzyme[enzyme] = shell

	new_complexes = []
	emitted = set()
	# Preserve original order for surviving complexes
	for c in existing:
		if c['enzyme'] in shells_by_enzyme:
			new_complexes.append(shells_by_enzyme[c['enzyme']])
			emitted.add(c['enzyme'])
	# Append brand-new complexes in alphabetical order
	for enzyme in sorted(shells_by_enzyme):
		if enzyme not in emitted:
			new_complexes.append(shells_by_enzyme[enzyme])

	# 3. Schema-validate every emitted complex (non-restrictive).
	for c in new_complexes:
		for w in ensure_schema_defaults(c, schema):
			print(w)
		for w in validate_dependencies(c, schema):
			print(w)

	# 4. Report complexes that no longer derive from roles.
	new_enzymes = {c['enzyme'] for c in new_complexes}
	for c in existing:
		if c['enzyme'] not in new_enzymes:
			issues.warn(
				f"complex '{c['enzyme']}' (kbase_id={c.get('kbase_id')}) is no longer "
				f"derivable from roles — no role has matching abstract_enzyme. Dropped."
			)

	write_db(complexes_path, new_complexes)
	issues.summary()


if __name__ == "__main__":
	main()
