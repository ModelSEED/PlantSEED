#!/usr/bin/env python
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


# Schema type names mirror Validate_Plantseed_Schema.py — keep the two in sync.
TYPE_MAP = {
	'str': str,
	'bool': bool,
	'list': list,
	'dict': dict,
	'int': int,
	'float': float,
}

# Minimum column count (including the enzyme and action columns) for each action.
ACTION_MIN_COLS = {
	'UPDATE':   3,  # enzyme  UPDATE   new_name
	'NEW':      2,  # enzyme  NEW
	'ADD':      4,  # enzyme  ADD      field  entry  [extra]
	'REMOVE':   4,  # enzyme  REMOVE   field  entry
	'RELOCATE': 5,  # enzyme  RELOCATE field  old   new
	'REASSIGN': 4,  # enzyme  REASSIGN field  value
	'ASSIGN':   4,  # DEPRECATED alias of REASSIGN
	'CHANGE':   4,  # DEPRECATED alias of REASSIGN
}

# Old action names that are now aliased onto REASSIGN. Curators using these
# still get the expected behaviour; a single end-of-parse warning per name
# tells them to switch.
DEPRECATED_REASSIGN_ALIASES = ('ASSIGN', 'CHANGE')


def parse_tsv(path, schema=None, issues=None):
	"""Read a curation TSV and bucket each line by action.

	Reports problems (unknown actions, malformed lines, unknown field names) to `issues`
	when supplied. Non-restrictive: bad lines are skipped, good lines still parsed."""
	actions = {
		'replace':  dict(),   # UPDATE: rename old role -> new role
		'new':      list(),   # NEW: empty role to add
		'add':      dict(),   # ADD: append to list/dict fields
		'rem':      dict(),   # REMOVE: drop from list/dict fields
		'key':      dict(),   # RELOCATE: rekey a dict entry
		'reassign': dict(),   # REASSIGN (and the deprecated ASSIGN/CHANGE aliases): set a scalar field
	}
	deprecated_alias_counts = {name: 0 for name in DEPRECATED_REASSIGN_ALIASES}

	def _check_field(field, lineno):
		if schema is not None and field not in schema and issues is not None:
			issues.warn(f"line {lineno}: field '{field}' is not in the schema — proceeding anyway")

	with open(path) as updates_file:
		for lineno, line in enumerate(updates_file.readlines(), start=1):
			line = line.strip('\r\n')

			if line.startswith('#') or not line.strip():
				continue

			tmp_lst = line.split('\t')
			if len(tmp_lst) < 2:
				if issues is not None:
					# A non-empty line that splits to one column almost always means the
					# user separated columns with spaces instead of TABs (a common issue
					# when editors auto-convert tabs to spaces).
					hint = ""
					if len(line.split()) > 1:
						hint = " — columns must be TAB-separated; this line looks space-separated"
					issues.warn(f"line {lineno}: fewer than 2 columns{hint} — skipped")
				continue

			enzyme = tmp_lst[0]
			action = tmp_lst[1].upper()

			if action not in ACTION_MIN_COLS:
				if issues is not None:
					issues.warn(f"line {lineno}: unknown action '{tmp_lst[1]}' (known: {sorted(ACTION_MIN_COLS)}) — skipped")
				continue

			if len(tmp_lst) < ACTION_MIN_COLS[action]:
				if issues is not None:
					issues.warn(
						f"line {lineno}: action {action} requires at least {ACTION_MIN_COLS[action]} columns, "
						f"got {len(tmp_lst)} — skipped"
					)
				continue

			# UPDATE: change the role name. Creates a new entry, removes the old.
			if action == "UPDATE":
				new_enzyme = tmp_lst[2]
				actions['replace'][enzyme] = new_enzyme

			# NEW: add a brand-new (empty-defaults) role.
			# Should be followed by ADD lines to populate it.
			elif action == "NEW":
				actions['new'].append(enzyme)
				print("Warning: is this enzyme conserved!", enzyme)

			# ADD: append to a list field, or key into a dict field.
			# Some fields take a key-value pair; others take a single entry.
			elif action == "ADD":
				field = tmp_lst[2]
				entry = tmp_lst[3]
				_check_field(field, lineno)
				if enzyme not in actions['add']:
					actions['add'][enzyme] = dict()
				if field not in actions['add'][enzyme]:
					actions['add'][enzyme][field] = dict()
				actions['add'][enzyme][field][entry] = 1
				if len(tmp_lst) > 4:
					entry_key = tmp_lst[3]
					entry_value = tmp_lst[4]
					actions['add'][enzyme][field][entry_key] = entry_value

			# REMOVE: drop an entry from a field.
			elif action == "REMOVE":
				field = tmp_lst[2]
				entry = tmp_lst[3]
				_check_field(field, lineno)
				if enzyme not in actions['rem']:
					actions['rem'][enzyme] = dict()
				if field not in actions['rem'][enzyme]:
					actions['rem'][enzyme][field] = list()
				actions['rem'][enzyme][field].append(entry)

			# RELOCATE: rekey a dict entry (e.g. move a feature between compartments).
			# Cascades to compartmentalization where applicable.
			elif action == "RELOCATE":
				field = tmp_lst[2]
				entry = tmp_lst[3]
				new_entry = tmp_lst[4]
				_check_field(field, lineno)
				if enzyme not in actions['key']:
					actions['key'][enzyme] = dict()
				if field not in actions['key'][enzyme]:
					actions['key'][enzyme][field] = dict()
				actions['key'][enzyme][field][entry] = new_entry

			# REASSIGN: set a scalar field (abstract_enzyme, type, ...).
			# ASSIGN and CHANGE are deprecated aliases — they route to the same
			# bucket so existing TSVs keep working.
			elif action in ("REASSIGN",) + DEPRECATED_REASSIGN_ALIASES:
				field = tmp_lst[2]
				entry = tmp_lst[3]
				_check_field(field, lineno)
				if enzyme not in actions['reassign']:
					actions['reassign'][enzyme] = dict()
				actions['reassign'][enzyme][field] = entry
				if action in DEPRECATED_REASSIGN_ALIASES:
					deprecated_alias_counts[action] += 1

	# Single end-of-parse warning per deprecated alias actually used.
	if issues is not None:
		for old_name in DEPRECATED_REASSIGN_ALIASES:
			count = deprecated_alias_counts[old_name]
			if count:
				issues.warn(
					f"action '{old_name}' is deprecated — please use 'REASSIGN' instead "
					f"({count} occurrence(s) in this file; behaviour is unchanged)"
				)

	return actions


def load_schema(yaml_path):
	"""Load PlantSEED_Schema.yaml. Mirrors Validate_Plantseed_Schema.py:load_schema,
	with added support for an optional `depends_on:` block per field."""
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


def default_role_from_schema(schema):
	"""Build the default empty-role dict from the schema's required fields.
	Deep-copies mutable defaults so each new role gets its own."""
	return {k: copy.deepcopy(rules['default']) for k, rules in schema.items() if rules['required']}


def seed_new_entries(roles_list, new_list, schema, actions=None, issues=None):
	"""Append default-shaped entries for each NEW role. Reports all collisions
	together before aborting (vs. the original single-collision sys.exit).

	abstract_enzyme is required; if the TSV doesn't set it explicitly via
	REASSIGN (or its deprecated ASSIGN/CHANGE aliases), default it to the
	role name with any " (EC ...)" suffix stripped, and warn the curator
	that this default was used."""
	existing = {entry['role'] for entry in roles_list}
	collisions = [new for new in new_list if new in existing]
	if collisions:
		for c in collisions:
			if issues is not None:
				issues.error(f"NEW role already present in database: '{c}'")
			else:
				print(f"Warning, New Role already present: {c}")
		sys.exit(1)

	for new in new_list:
		new_role = default_role_from_schema(schema)
		new_role['role'] = new
		new_role['abstract_enzyme'] = new.split(' (EC')[0]

		explicit_abstract = actions is not None and (
			'abstract_enzyme' in actions.get('reassign', {}).get(new, {})
		)
		if not explicit_abstract and issues is not None:
			issues.warn(
				f"NEW role '{new}': abstract_enzyme not provided — "
				f"defaulting to '{new_role['abstract_enzyme']}' (role name with EC stripped). "
				f"Set it explicitly with a REASSIGN row if a different value is wanted."
			)

		roles_list.append(new_role)


def apply_actions(roles_list, actions, input_file, issues=None):
	"""Apply parsed actions to roles_list in place.
	Returns (touched_role_names, rename_map old->new)."""
	replace_dict  = actions['replace']
	add_dict      = actions['add']
	rem_dict      = actions['rem']
	key_dict      = actions['key']
	reassign_dict = actions['reassign']

	touched = set()
	rename_map = dict()

	for entry in roles_list:
		updated_role = False

		# Rename first — subsequent lookups use the new name.
		if entry['role'] in replace_dict:
			old_name = entry['role']
			entry['role'] = replace_dict[old_name]
			rename_map[old_name] = entry['role']
			updated_role = True

		# ADD pass: append entries and cascade into localization / classes / compartmentalization.
		if entry['role'] in add_dict:
			for field in add_dict[entry['role']]:
				if field not in entry:
					entry[field] = list()

				for input_value in add_dict[entry['role']][field]:

					if input_value not in entry[field]:
						entry[field].append(input_value)

					# Feature → localization cascade. Localization col is OPTIONAL —
					# omit silently if not given. If given, it MUST be "compartment:code".
					if field == 'features':
						raw = add_dict[entry['role']][field][input_value]
						if raw == 1:
							pass  # no localization provided — optional, skip cascade
						elif ':' not in raw:
							msg = (
								f"feature '{input_value}' for role '{entry['role']}': "
								f"localization value '{raw}' is missing a ':' separator "
								f"(expected 'compartment:source-code', e.g. 'c:PPDB') — "
								f"feature added but no localization recorded"
							)
							if issues is not None:
								issues.warn(msg)
							else:
								print(f"[WARN] {msg}")
						else:
							(cpt, code) = raw.split(':', 1)
							if cpt in entry['localization']:
								entry['localization'][cpt][input_value] = [code]
							else:
								entry['localization'][cpt] = {input_value: [code]}

					# Subsystem → classes cascade. Class col is OPTIONAL — silent skip
					# when not given. (The sentinel for "no class" is the int 1 set by
					# parse_tsv; the original `== "1"` string comparison was a bug.)
					if field == 'subsystems':
						sys_cls = add_dict[entry['role']][field][input_value]
						if sys_cls == 1:
							pass  # no class provided — optional, skip cascade
						else:
							if 'classes' not in entry:
								entry['classes'] = dict()
							if sys_cls not in entry['classes']:
								entry['classes'][sys_cls] = dict()
							entry['classes'][sys_cls][input_value] = []

					# Reaction → localization cascade (assumed compartment).
					if field == 'reactions':
						if add_dict[entry['role']][field][input_value] == 1:
							continue
						cpt = add_dict[entry['role']][field][input_value]
						if 'localization' not in entry:
							entry['localization'] = dict()
						if cpt not in entry['localization']:
							entry['localization'][cpt] = dict()
						entry['localization'][cpt][input_value] = ["Assumed"]

			updated_role = True

		if entry['role'] in reassign_dict:
			for field in reassign_dict[entry['role']]:
				entry[field] = reassign_dict[entry['role']][field]
			updated_role = True

		# RELOCATE: rekey within a dict field; cascade into compartmentalization.
		if entry['role'] in key_dict:
			print(entry['role'])

			for field in key_dict[entry['role']]:

				for old_entry in key_dict[entry['role']][field]:
					new_entry = key_dict[entry['role']][field][old_entry]

					if old_entry not in entry[field]:
						print("Warning, old entry not found in field: " + old_entry)
						continue

					entry[field][new_entry] = entry[field][old_entry]
					del entry[field][old_entry]

					if old_entry in entry.get('compartmentalization', {}):
						new_hash = copy.deepcopy(entry['compartmentalization'][old_entry])
						new_hash['reaction'] = new_entry
						for kbid in new_hash['kbase_ids']:
							for rxn_idx in range(len(new_hash['kbase_ids'][kbid])):
								rxn = new_hash['kbase_ids'][kbid][rxn_idx]
								rxn = rxn.replace('_' + old_entry, '_' + new_entry)
								new_hash['kbase_ids'][kbid][rxn_idx] = rxn

						entry['compartmentalization'][new_entry] = new_hash
						del entry['compartmentalization'][old_entry]
					updated_role = True

		# REMOVE: drop entries; cascade out of localization for features.
		if entry['role'] in rem_dict:
			for field in rem_dict[entry['role']]:
				for input_value in rem_dict[entry['role']][field]:
					if isinstance(entry[field], list):
						entry[field].remove(input_value)
					elif isinstance(entry[field], dict):
						del entry[field][input_value]

					if field == 'features':
						delete_cpts = list()
						for cpt in entry['localization']:
							if input_value in entry['localization'][cpt]:
								del entry['localization'][cpt][input_value]
							if len(entry['localization'][cpt]) == 0:
								delete_cpts.append(cpt)

						for cpt in delete_cpts:
							del entry['localization'][cpt]

			updated_role = True

		if updated_role:
			# Curator inferred from the input-file path: Curators/<github-username>/...
			if 'curators' not in entry:
				entry['curators'] = list()

			input_directory = os.path.dirname(os.path.abspath(input_file))
			tmp_dirs = input_directory.split('/')
			curator = tmp_dirs[tmp_dirs.index('Curators') + 1]

			if curator not in entry['curators']:
				entry['curators'].append(curator)

			touched.add(entry['role'])

	return touched, rename_map


def ensure_schema_defaults(entry, schema):
	"""Fill missing required fields with their schema default. Non-restrictive: warn, never fail.
	Returns a list of warning messages."""
	warnings = []
	role_name = entry.get('role', '<unnamed>')
	for key, rules in schema.items():
		if not rules['required']:
			continue
		if key not in entry:
			entry[key] = copy.deepcopy(rules['default'])
			warnings.append(f"[DEFAULT FILLED] '{key}' was missing in role '{role_name}' — set to default {rules['default']!r}")
	return warnings


def validate_dependencies(entry, schema):
	"""Check cross-field dependencies declared via `depends_on` in the schema.
	Non-restrictive: emit warnings only; do not mutate the entry."""
	warnings = []
	role_name = entry.get('role', '<unnamed>')

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
						f"[DEPENDENCY WARNING] '{key}' key '{k}' in role '{role_name}' "
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
							f"in role '{role_name}' is not present in {dep['inner_keys_from']}"
						)

	return warnings


def assign_kbase_id(entry, existing_ids, renamed_from=None):
	"""Compute PS_role_<sha256[:6]> from role + reactions[0] + subsystems[0].
	Mirrors Prepare_PlantSEED_KBase.py:27-51. Returns True if entry['kbase_id'] changed.
	On rename, recomputes and warns loudly."""
	role_name = entry.get('role', '<unnamed>')

	if not entry.get('role') or not entry.get('reactions') or not entry.get('subsystems'):
		if renamed_from is not None or 'kbase_id' not in entry:
			print(f"Warning, missing role, reactions, or subsystems for role: {role_name}")
			print("\tCannot create unique KBase Role ID")
		return False

	# Existing role with a kbase_id and no rename → leave it alone.
	if 'kbase_id' in entry and renamed_from is None:
		return False

	old_id = entry.get('kbase_id')
	role_str = entry['role'] + entry['reactions'][0] + entry['subsystems'][0]
	entry_id = 'PS_role_' + hashlib.sha256(role_str.encode('utf-8')).hexdigest()[:6]

	# Drop the old id from the pool so a rehash can land on the same slot if applicable.
	pool = set(existing_ids)
	if old_id in pool:
		pool.discard(old_id)

	while entry_id in pool:
		entry_id = 'PS_role_' + hashlib.sha256(entry_id.encode('utf-8')).hexdigest()[:6]

	if entry_id == old_id:
		return False

	entry['kbase_id'] = entry_id
	existing_ids.discard(old_id) if old_id else None
	existing_ids.add(entry_id)

	if renamed_from is not None and old_id is not None:
		print(
			f"WARN: kbase_id changed for renamed role '{role_name}' "
			f"(was {old_id}, now {entry_id}) — downstream KBase consumers may need to remap."
		)

	return True


def write_db(path, roles_list):
	with open(path, 'w') as f:
		json.dump(roles_list, f, indent=4)


def main():
	issues = Issues()

	if len(sys.argv) < 2:
		print("Error: missing argument.")
		print("Usage: Update_Enzymes_in_PlantSEED.py <path-to-updates.tsv>")
		sys.exit(1)

	input_file = sys.argv[1]
	if not os.path.isfile(input_file):
		print(f"Error: input file does not exist: {input_file}")
		print("Check the path and try again.")
		sys.exit(1)

	script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
	database_relative_path = os.path.join(script_directory, "../../../", "Data/PlantSEED_v3/")
	roles_path = os.path.join(database_relative_path, "PlantSEED_Roles.json")
	schema_path = os.path.join(script_directory, "PlantSEED_Schema.yaml")

	schema = load_schema(schema_path)
	actions = parse_tsv(input_file, schema=schema, issues=issues)

	with open(roles_path) as f:
		roles_list = json.load(f)

	# Warn if any action targets a role name that doesn't exist in the database.
	# UPDATE/ADD/REMOVE/RELOCATE/REASSIGN all key off an existing role name.
	# Include NEW roles too — they'll exist after seed_new_entries, so ADDs that
	# follow a NEW in the same TSV are valid.
	known_roles = {entry['role'] for entry in roles_list} | set(actions['new'])
	bucket_to_action = {'replace': 'UPDATE', 'add': 'ADD', 'rem': 'REMOVE',
	                    'key': 'RELOCATE', 'reassign': 'REASSIGN'}
	for bucket, action_name in bucket_to_action.items():
		for role_name in actions[bucket]:
			if role_name not in known_roles:
				issues.warn(
					f"role '{role_name}' not found in database — its {action_name} action(s) will be ignored"
				)

	seed_new_entries(roles_list, actions['new'], schema, actions=actions, issues=issues)
	# Newly-seeded roles are also "touched" — include them so they get validated and hashed.
	touched, rename_map = apply_actions(roles_list, actions, input_file, issues=issues)
	touched.update(actions['new'])

	if not touched:
		issues.summary()
		return

	# Reverse rename map so we can look up "what was this role called before?"
	reverse_rename = {new: old for old, new in rename_map.items()}

	existing_ids = {entry['kbase_id'] for entry in roles_list if 'kbase_id' in entry}

	for entry in roles_list:
		if entry['role'] not in touched:
			continue

		for w in ensure_schema_defaults(entry, schema):
			print(w)
		for w in validate_dependencies(entry, schema):
			print(w)

		renamed_from = reverse_rename.get(entry['role'])
		assign_kbase_id(entry, existing_ids, renamed_from=renamed_from)

	write_db(roles_path, roles_list)
	issues.summary()


if __name__ == "__main__":
	main()
