module PlantSEED
{
    typedef structure {
    	string id;
	string type;
	string function;
	string aliases;
	string contig;
	int begin;
	int end;
    } feature;

    typedef structure {
    	string id;
	string name;
	int begin;
	int end;
	list<feature> features;
    } region;
    
    typedef structure {
    	int size;
	int number;
	mapping<string region_id, mapping<region> regions;
    } regions;
};
