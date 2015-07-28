module PlantSEED
{
    typedef structure {
    	string id;
	string source;
	string scientific_name;
	string taxonomy;
	mapping<string feature_id, int sim_index> similarities_index;
        list<minimal_feature> features;
    } minimal_genome;
    
    typedef structure {
    	string id;
	string function;
	list<string> subsystems;
    } minimal_feature;
};
