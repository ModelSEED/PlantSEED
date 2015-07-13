module PlantSEED
{
    typedef structure {
    	string id;
	string source;
	string scientific_name;
	string taxonomy;
	list<sim_index> similarities_index;
        list<minimal_feature> features;
    } minimal_genome;
    
    typedef structure {
    	string id;
	string function;
	list<string> subsystems;
    } minimal_feature;

    typedef structure {
    	string feature_id;
	int index;
    } sim_index;	
};
