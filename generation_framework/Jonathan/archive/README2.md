
The source is located [here](https://pitt-my.sharepoint.com/personal/jos220_pitt_edu/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fjos220%5Fpitt%5Fedu%2FDocuments%2FOWLNETS%2DUMLS%2DGRAPH)
The script 'transform.py' is used to add input and output directories to this script which assumes that all files are in the same directory.

Uberon only test cases...

MATCH (:Concept)-[r:inverse_isa]->(:Concept) WHERE r.SAB = 'UBERON' RETURN COUNT(r)
36241

MATCH (c:Code)-[r:PT]->(t:Term) WHERE c.SAB = 'UBERON' RETURN COUNT(r)
14140

MATCH (c:Code)-[r:SY]->(t:Term) WHERE c.SAB = 'UBERON' RETURN COUNT(r)
37046

MATCH (c:Concept)-[r]->(t:Code) WHERE t.SAB = 'UBERON' RETURN COUNT(r)
15716

Uberon & CL only....

MATCH (:Concept)-[r:inverse_isa]->(:Concept) WHERE r.SAB IN ['CL', 'UBERON'] RETURN COUNT(r)
56341

MATCH (c:Code)-[r:PT]->(t:Term) WHERE c.SAB IN ['CL', 'UBERON'] RETURN COUNT(r)
23334

MATCH (c:Code)-[r:SY]->(t:Term) WHERE c.SAB IN ['CL', 'UBERON'] RETURN COUNT(r)
56877

MATCH (c:Concept)-[r]->(t:Code) WHERE t.SAB IN ['CL', 'UBERON'] RETURN COUNT(r)
20020
