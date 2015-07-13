module PlantSEED
{    
    typedef structure {
        string id;
	string function;
	string protein_translation;
	list<string> subsystems;
	list<similarity> plant_similarities;
	list<similarity> prokaryotic_similarities;
    } feature;

    typedef structure {
        string hit_id;
	float percent_id;
	float e_value;
	int bit_score;
    } similarity;
};
