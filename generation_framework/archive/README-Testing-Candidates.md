#  Testing Candidates

The following are a set of match [Cypher queries](https://neo4j.com/developer/cypher/) as candidates for testing the .owl to .csv generation fround in the './scripts' directory after loading them into a Neo4J database using [neof4-admin import](https://neo4j.com/docs/operations-manual/current/tutorial/neo4j-admin-import/). This is done in the Docker file in the './neo4j' directory in this project to build the database.

They may or may not be useful at some point. These are a set of notes, some of which will be codified into a set of tests to be run on the database.

## Checking for zero pref-terms
To see if not equal 1 is zero or more than 1. If there are none of those then it's a duplication problem which is less serious in a sense than a missing pref-term problem - either way, need to make a tiny adjustment to catch some duplication or catch some missing labels in node_metadata. Should not be a big deal, but will have to address.

```buildoutcfg
MATCH (a:Concept) WHERE size((a)-[:PREF_TERM]->(:Term))=0 RETURN COUNT(a)
```

## Substituting each new SAB being introduced, check the chain from CUI through code to preferred term

For some ontologies the match isn’t perfect but it's close (possibly an issue with missing node_label).

```buildoutcfg
MATCH p=((a:Concept)-->(b:Code{SAB:'PATO'})-[c:PT]->(:Term)) WHERE a.CUI = c.CUI RETURN COUNT(p),COUNT(DISTINCT b)
```

## Count total Codes in all SABs at once

The results should all match up similar to the above counts - difference is the total of those in node_metadata without Labels. Have to decide what to do about that - one approach is to recognize we’re taking as much information as we’re given so we build anyway even if no Labels whereas the other approach is to not allow an addition to the graph unless it has a Label.

```buildoutcfg
MATCH (r:Code) RETURN r.SAB, COUNT(r) ORDER BY r.SAB
```

## Count unidirectional (div 2) CUI-CUI relationships by all SABs at once
```buildoutcfg
MATCH (:Concept)-[r]->(:Concept) RETURN r.SAB, COUNT(r)/2 ORDER BY r.SAB
```


Code for checking how many CUI do not have Semantic (not an acceptance requirement that it be zero - generally run before and after running below approaches to demonstrate number of Semantics assigned programmatically:
```buildoutcfg
MATCH (b:Concept) WHERE SIZE((b)-->(:Semantic)) = 0 RETURN COUNT(b)
```

### Code for adding Semantic via graph propogation

Candidate is the two commands below
 
Code for adding Semantic via graph propogation (candidate is the two commands below): 

```buildoutcfg
MATCH (b:Concept) WHERE SIZE((b)-->(:Semantic)) = 0
CALL { WITH b
MATCH p=((b)-[:isa*1..2]->(c:Concept)-->(d:Semantic)) 
RETURN LENGTH(p), d.STN, b AS Cncpt, d AS Smntc ORDER BY LENGTH(p), d.STN DESCENDING LIMIT 1 }
CREATE (Cncpt)-[:STY]->(Smntc);
```

Run above repeating until 0 new relationships written (using the "rerun" button on graphical bolt interface), then run below only once.

Explanation of repeating: Above could in theory be done as a longer variable length query rather than repeat, but longer doesn't complete in reasonable time - the variable length longer results in a huge memory-intensive computation - repeating two segments at a time ran less than one minute each and only a few repeats were needed to saturate to zero more relationships created - so repeating is best approach with modest analysis. Also note that its less precise and certainly not "valid" to run below more than once - below allows up and down directions and part_of to catch some "stragglers".

```buildoutcfg
MATCH (b:Concept) WHERE SIZE((b)-->(:Semantic)) = 0
CALL { WITH b
MATCH p=((b)-[:isa|part_of*1..2]-(c:Concept)-->(d:Semantic)) 
RETURN LENGTH(p), d.STN, b AS Cncpt, d AS Smntc ORDER BY LENGTH(p), d.STN DESCENDING LIMIT 1 }
CREATE (Cncpt)-[:STY]->(Smntc);
```

List all the unique SABs of Codes.

```buildoutcfg
match (a:Code) return distinct a.SAB order by a.SAB
```
