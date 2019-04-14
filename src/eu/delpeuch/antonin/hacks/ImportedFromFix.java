package eu.delpeuch.antonin.hacks;

import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.io.LineNumberReader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import org.apache.jena.query.Query;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSet;
import org.wikidata.wdtk.datamodel.helpers.Datamodel;
import org.wikidata.wdtk.datamodel.helpers.StatementBuilder;
import org.wikidata.wdtk.datamodel.interfaces.ItemDocument;
import org.wikidata.wdtk.datamodel.interfaces.ItemIdValue;
import org.wikidata.wdtk.datamodel.interfaces.PropertyIdValue;
import org.wikidata.wdtk.datamodel.interfaces.Reference;
import org.wikidata.wdtk.datamodel.interfaces.Snak;
import org.wikidata.wdtk.datamodel.interfaces.SnakGroup;
import org.wikidata.wdtk.datamodel.interfaces.SomeValueSnak;
import org.wikidata.wdtk.datamodel.interfaces.Statement;
import org.wikidata.wdtk.datamodel.interfaces.StatementGroup;
import org.wikidata.wdtk.datamodel.interfaces.ValueSnak;
import org.wikidata.wdtk.wikibaseapi.ApiConnection;
import org.wikidata.wdtk.wikibaseapi.LoginFailedException;
import org.wikidata.wdtk.wikibaseapi.WikibaseDataEditor;
import org.wikidata.wdtk.wikibaseapi.WikibaseDataFetcher;
import org.wikidata.wdtk.wikibaseapi.apierrors.MediaWikiApiErrorException;

public class ImportedFromFix {
	
	static PropertyIdValue imported_from_pid = Datamodel.makePropertyIdValue("P143", Datamodel.SITE_WIKIDATA);
	static PropertyIdValue stated_in = Datamodel.makePropertyIdValue("P248", Datamodel.SITE_WIKIDATA);
	
	public static Reference translateReference(Reference orig, Set<String> allowedUris) {
		return Datamodel.makeReference(orig.getSnakGroups().stream()
				.map(sg -> Datamodel.makeSnakGroup(
						sg.getSnaks().stream().map(s -> translateSnak(s, allowedUris)).collect(Collectors.toList())))
				.collect(Collectors.toList()));
	}
	
	public static Snak translateSnak(Snak snak, Set<String> allowedUris) {
		if (snak.getPropertyId().equals(imported_from_pid) && snak instanceof ValueSnak &&
				snak.getValue() instanceof ItemIdValue && allowedUris.contains(((ItemIdValue)snak.getValue()).getIri())) {
			return Datamodel.makeValueSnak(stated_in, snak.getValue());
		} else {
			return snak;
		}
	}
	
	
	public static void refFix(String password) throws MediaWikiApiErrorException, IOException, LoginFailedException {
		ApiConnection conn = ApiConnection.getWikidataApiConnection();
		WikibaseDataFetcher fetcher = new WikibaseDataFetcher(conn, Datamodel.SITE_WIKIDATA);
		WikibaseDataEditor editor = new WikibaseDataEditor(conn, Datamodel.SITE_WIKIDATA);
		conn.login("PintochBot", password);
		editor.setRemainingEdits(10);
		editor.setEditAsBot(true);
		
		FileReader fileReader = new FileReader(new File("safe_values_to_fix.tsv"));
		LineNumberReader reader = new LineNumberReader(fileReader);
		Set<String> allowedValues = reader.lines().map(s -> s.trim()).collect(Collectors.toSet());

		
		//Snak refSnak = Datamodel.makeValueSnak(p356, Datamodel.makeStringValue("10.5281/zenodo.758080"));
		//Reference goodReference = Datamodel.makeReference(Collections.singletonList(Datamodel.makeSnakGroup(Collections.singletonList(refSnak))));
		
		// Loop through items to fix
		Query query = QueryFactory.create( 
				" PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n" + 
				" PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n" + 
				" PREFIX ontolex: <http://www.w3.org/ns/lemon/ontolex#>\n" + 
				" PREFIX dct: <http://purl.org/dc/terms/>\n" + 
				" PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n" + 
				" PREFIX owl: <http://www.w3.org/2002/07/owl#>\n" + 
				" PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n" + 
				" PREFIX schema: <http://schema.org/>\n" + 
				" PREFIX cc: <http://creativecommons.org/ns#>\n" + 
				" PREFIX geo: <http://www.opengis.net/ont/geosparql#>\n" + 
				" PREFIX prov: <http://www.w3.org/ns/prov#>\n" + 
				" PREFIX wikibase: <http://wikiba.se/ontology#>\n" + 
				" PREFIX wdata: <http://www.wikidata.org/wiki/Special:EntityData/>\n" + 
				" PREFIX bd: <http://www.bigdata.com/rdf#>\n" + 
				" \n" + 
				" PREFIX wd: <http://www.wikidata.org/entity/>\n" + 
				" PREFIX wdt: <http://www.wikidata.org/prop/direct/>\n" + 
				" PREFIX wdtn: <http://www.wikidata.org/prop/direct-normalized/>\n" + 
				" \n" + 
				" PREFIX wds: <http://www.wikidata.org/entity/statement/>\n" + 
				" PREFIX p: <http://www.wikidata.org/prop/>\n" + 
				" PREFIX wdref: <http://www.wikidata.org/reference/>\n" + 
				" PREFIX wdv: <http://www.wikidata.org/value/>\n" + 
				" PREFIX ps: <http://www.wikidata.org/prop/statement/>\n" + 
				" PREFIX psv: <http://www.wikidata.org/prop/statement/value/>\n" + 
				" PREFIX psn: <http://www.wikidata.org/prop/statement/value-normalized/>\n" + 
				" PREFIX pq: <http://www.wikidata.org/prop/qualifier/>\n" + 
				" PREFIX pqv: <http://www.wikidata.org/prop/qualifier/value/>\n" + 
				" PREFIX pqn: <http://www.wikidata.org/prop/qualifier/value-normalized/>\n" + 
				" PREFIX pr: <http://www.wikidata.org/prop/reference/>\n" + 
				" PREFIX prv: <http://www.wikidata.org/prop/reference/value/>\n" + 
				" PREFIX prn: <http://www.wikidata.org/prop/reference/value-normalized/>\n" + 
				" PREFIX wdno: <http://www.wikidata.org/prop/novalue/>\n"
				+ "PREFIX hint: <http://www.bigdata.com/queryHints#> \n"
				+ "SELECT ?item ?db WHERE {\n" + 
				"  ?item ?prop ?statement.\n" + 
				"  ?statement prov:wasDerivedFrom/pr:P143 ?db.\n" + 
				"  {\n" + 
				"     ?db wdt:P31/wdt:P279* wd:Q2352616 .\n"
				+ "hint:Prior hint:gearing \"forward\".\n" + 
				"  } UNION {\n" + 
				"     ?db wdt:P31/wdt:P279* wd:Q386724 .\n"
				+ "hint:Prior hint:gearing \"forward\".\n" + 
				"  } UNION {\n" + 
				"     ?db wdt:P31/wdt:P279* wd:Q3331189 .\n"
				+ "hint:Prior hint:gearing \"forward\".\n" + 
				"  } UNION {\n" + 
				"     ?db wdt:P31/wdt:P279* wd:Q11028.\n"
				+ "hint:Prior hint:gearing \"forward\".\n" + 
				"  }\n" + 
				"  MINUS { ?db wdt:P31/wdt:P279* wd:Q14827288 }\n" + 
				"} LIMIT 1000\n");
		
		boolean itemFound = true;
		
		while(itemFound) {
			itemFound = false;
			QueryExecution queryExec = QueryExecutionFactory.sparqlService("https://query.wikidata.org/sparql", query);
			
			// Loop through statements
			ResultSet rs = queryExec.execSelect();
			while (rs.hasNext()) {
				// Copy statement, fixing references
				QuerySolution qs = rs.next();
				String qid = qs.get("item").toString().substring("http://www.wikidata.org/entity/".length());
				System.out.println(qid);
				ItemDocument doc = (ItemDocument) fetcher.getEntityDocument(qid);
	
				List<Statement> newStatements = new ArrayList<>();
				Iterator<Statement> statements = doc.getAllStatements();
				while(statements.hasNext()) {
					Statement statement = statements.next();
					List<Reference> newReferences = statement.getReferences().stream().map(r -> translateReference(r, allowedValues)).collect(Collectors.toList());
					if (!newReferences.equals(statement.getReferences())) {
						StatementBuilder newStatementBuilder = StatementBuilder.forSubjectAndProperty(statement.getSubject(), statement.getClaim().getMainSnak().getPropertyId())
								.withId(statement.getStatementId());
						if(statement.getClaim().getMainSnak() instanceof ValueSnak) {
							newStatementBuilder.withValue(statement.getClaim().getMainSnak().getValue());
						} else if(statement.getClaim().getMainSnak() instanceof SomeValueSnak) {
							newStatementBuilder.withSomeValue();
						} else {
							newStatementBuilder.withNoValue();
						}
						for(SnakGroup qualifier : statement.getQualifiers()) {
							newStatementBuilder.withQualifiers(qualifier);
						}
						Statement newStatement = newStatementBuilder.withReferences(newReferences).build();
						newStatements.add(newStatement);
					}
				}
				if(!newStatements.isEmpty()) {
					System.out.println("Updating statements");
					editor.updateStatements(doc, newStatements, Collections.emptyList(), "migrate reference from [[Property:P143]] to [[Property:P248]]");
				} else {
					System.out.println("No statement to change");
				}
			}
		}
	}
}
