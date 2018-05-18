package eu.delpeuch.antonin.hacks;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import org.apache.jena.query.Query;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSet;
import org.wikidata.wdtk.datamodel.helpers.Datamodel;
import org.wikidata.wdtk.datamodel.interfaces.ItemDocument;
import org.wikidata.wdtk.datamodel.interfaces.MonolingualTextValue;
import org.wikidata.wdtk.wikibaseapi.ApiConnection;
import org.wikidata.wdtk.wikibaseapi.WikibaseDataEditor;
import org.wikidata.wdtk.wikibaseapi.WikibaseDataFetcher;

public class ArticleTitleBracketFix {
	public static void bracketTitleFix(String password) throws Exception {
		ApiConnection conn = ApiConnection.getWikidataApiConnection();
		WikibaseDataFetcher fetcher = new WikibaseDataFetcher(conn, Datamodel.SITE_WIKIDATA);
		WikibaseDataEditor editor = new WikibaseDataEditor(conn, Datamodel.SITE_WIKIDATA);
		conn.login("PintochBot", password);
		editor.setEditAsBot(true);
		
		Query query = QueryFactory.create(
				"PREFIX wdt: <http://www.wikidata.org/prop/direct/>\n" +
				"PREFIX wd: <http://www.wikidata.org/entity/>\n" +
				"PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n" + 
				" # Scientific articles with English titles in brackets\n" + 
				" # usually from PubMed, indicating that original language was not English\n" + 
				" SELECT ?paper ?paperLabel ?pmid WHERE {\n" + 
				"      ?paper wdt:P31 wd:Q13442814;\n" + 
				"             wdt:P698 ?pmid;\n" + 
				"             rdfs:label ?paperLabel\n" + 
				"      FILTER(lang(?paperLabel)=\"en\")\n" + 
				"      FILTER(STRSTARTS(?paperLabel, \"[\")).\n" + 
				"      FILTER(STRENDS(?paperLabel, \"]\")).\n" + 
				" } LIMIT 30\n" + 
				"\n" + 
				"");
		
		QueryExecution queryExec = QueryExecutionFactory.sparqlService("https://query.wikidata.org/sparql", query);
		
		// Loop through statements
		ResultSet rs = queryExec.execSelect();
		while (rs.hasNext()) {
			// Copy statement, fixing references
			QuerySolution qs = rs.next();
			String qid = qs.get("paper").toString().substring("http://www.wikidata.org/entity/".length());
			ItemDocument doc = (ItemDocument) fetcher.getEntityDocument(qid);
			System.out.println(qid);
			
			List<MonolingualTextValue> newLabels = new ArrayList<>();
			for(MonolingualTextValue label : doc.getLabels().values()) {
				String text = label.getText();
				if(text.startsWith("[") && text.endsWith("]")) {
					MonolingualTextValue newLabel = Datamodel.makeMonolingualTextValue(
							text.substring(1, text.length()-1), label.getLanguageCode());
					newLabels.add(newLabel);
					System.out.println(newLabel);
				}
			}
			editor.updateTermsStatements(doc, newLabels,
					Collections.emptyList(), Collections.emptyList(),
					Collections.emptyList(), Collections.emptyList(),
					Collections.emptyList(), "fixing brackets in labels");
		}
	}
}
