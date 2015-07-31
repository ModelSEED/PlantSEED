module PlantSEED
{
    typedef structure {
    	string id;
    } feature;

    typedef structure {
    	string name;
    } subsystem;

    typedef structure {
    	string id;
    } pathway;

    typedef structure {
    	string id;
    } reaction;

    typedef structure {
    	string role;
	list<subsystem> subsystems;
	list<feature> features;
	list<reaction> reactions;
	list<pathway> pathways;
    } annotation_overview;
};
