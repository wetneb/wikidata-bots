package eu.delpeuch.antonin.hacks;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

import org.apache.jena.query.Query;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSet;
import org.wikidata.wdtk.datamodel.helpers.Datamodel;
import org.wikidata.wdtk.datamodel.interfaces.ItemIdValue;
import org.wikidata.wdtk.datamodel.interfaces.PropertyDocument;
import org.wikidata.wdtk.datamodel.interfaces.PropertyIdValue;
import org.wikidata.wdtk.datamodel.interfaces.Snak;
import org.wikidata.wdtk.datamodel.interfaces.SnakGroup;
import org.wikidata.wdtk.datamodel.interfaces.Statement;
import org.wikidata.wdtk.datamodel.interfaces.StatementGroup;
import org.wikidata.wdtk.wikibaseapi.ApiConnection;
import org.wikidata.wdtk.wikibaseapi.WikibaseDataEditor;
import org.wikidata.wdtk.wikibaseapi.WikibaseDataFetcher;

public class ConstraintKrBotFix {
	public static void migrateConstraints(String password) throws Exception {
		ApiConnection conn = ApiConnection.getWikidataApiConnection();
		WikibaseDataFetcher fetcher = new WikibaseDataFetcher(conn, Datamodel.SITE_WIKIDATA);
		WikibaseDataEditor editor = new WikibaseDataEditor(conn, Datamodel.SITE_WIKIDATA);
		conn.login("PintochBot", password);
		editor.setEditAsBot(true);
		
		ItemIdValue scopeQid = Datamodel.makeWikidataItemIdValue("Q53869507");
		PropertyIdValue p2302 = Datamodel.makeWikidataPropertyIdValue("P2302");
		Map<String, String> qidMap = new HashMap<>();
		qidMap.put("Q46466787", "Q21528958"); // values
		qidMap.put("Q46466783","Q21510863"); // qualifiers
		qidMap.put("Q46466805", "Q21528959"); // references
		
		Query query = QueryFactory.create(
				"PREFIX wdt: <http://www.wikidata.org/prop/direct/>\n" +
				"PREFIX p: <http://www.wikidata.org/prop/>\n" +
				"PREFIX ps: <http://www.wikidata.org/prop/statement/>\n" +
				"PREFIX wd: <http://www.wikidata.org/entity/>\n" +
				"PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n" + 
				" SELECT ?item WHERE {\n" + 
				"  ?item p:P2302/ps:P2302 wd:Q53869507.\n" + 
				"  MINUS { ?item wdt:P31/wdt:P279* wd:Q19847637 }\n" + 
				"}\n"+
				"ORDER BY ?item\n"+
				"LIMIT 10");
		System.out.println(query.toString());
		
		QueryExecution queryExec = QueryExecutionFactory.sparqlService("https://query.wikidata.org/sparql", query);
		
		// Loop through properties
		ResultSet rs = queryExec.execSelect();
		while (rs.hasNext()) {
			QuerySolution qs = rs.next();
			String pid = qs.get("item").toString().substring("http://www.wikidata.org/entity/".length());

			System.out.println(pid);
			PropertyDocument doc = (PropertyDocument) fetcher.getEntityDocument(pid);
			
			StatementGroup constraints = doc.findStatementGroup("P2302");
			Optional<Statement> maybeScopeStatement = constraints.getStatements().stream()
					.filter(s -> scopeQid.equals(s.getClaim().getMainSnak().getValue()))
					.findFirst();
			if(!maybeScopeStatement.isPresent()) {
				continue;
			}
			Statement scopeStatement = maybeScopeStatement.get();
			
			List<Snak> currentLocations = scopeStatement.getClaim()
					.getQualifiers().stream()
					.filter(q -> "P4680".equals(q.getProperty().getId()))
					.map(q -> q.getSnaks())
					.findFirst().get();
			List<SnakGroup> otherQualifiers = scopeStatement.getClaim()
					.getQualifiers().stream()
					.filter(q -> ! "P4680".equals(q.getProperty().getId()))
					.collect(Collectors.toList());
			
			// Don't translate properties which are expected to have multiple locations
			if (currentLocations.size() != 1) {
				continue;
			}
			
			ItemIdValue newConstraintQid = Datamodel.makeWikidataItemIdValue(
					qidMap.get(((ItemIdValue)currentLocations.get(0).getValue()).getId()));
			Statement newStatement = Datamodel.makeStatement(
					Datamodel.makeClaim(doc.getEntityId(),
							Datamodel.makeValueSnak(p2302, newConstraintQid),
							otherQualifiers),
					scopeStatement.getReferences(),
					scopeStatement.getRank(),
					scopeStatement.getStatementId());
			
			editor.updateStatements(doc, Collections.singletonList(newStatement),
					Collections.emptyList(), "migrating back to the original format ([[:toollabs:editgroups/b/CB/782f83abc|details]])");
		}
	}
}
