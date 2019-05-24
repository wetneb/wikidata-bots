package eu.delpeuch.antonin.hacks;

import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.io.LineNumberReader;
import java.util.Collections;
import java.util.concurrent.TimeUnit;

import org.wikidata.wdtk.datamodel.helpers.Datamodel;
import org.wikidata.wdtk.datamodel.interfaces.Claim;
import org.wikidata.wdtk.datamodel.interfaces.ItemDocument;
import org.wikidata.wdtk.datamodel.interfaces.ItemIdValue;
import org.wikidata.wdtk.datamodel.interfaces.PropertyIdValue;
import org.wikidata.wdtk.datamodel.interfaces.Snak;
import org.wikidata.wdtk.datamodel.interfaces.Statement;
import org.wikidata.wdtk.datamodel.interfaces.StatementGroup;
import org.wikidata.wdtk.datamodel.interfaces.StatementRank;
import org.wikidata.wdtk.datamodel.interfaces.StringValue;
import org.wikidata.wdtk.wikibaseapi.ApiConnection;
import org.wikidata.wdtk.wikibaseapi.LoginFailedException;
import org.wikidata.wdtk.wikibaseapi.WikibaseDataEditor;
import org.wikidata.wdtk.wikibaseapi.WikibaseDataFetcher;
import org.wikidata.wdtk.wikibaseapi.apierrors.MediaWikiApiErrorException;

public class TwitterCaseFixer {
	public static PropertyIdValue pid = Datamodel.makeWikidataPropertyIdValue("P2002");
	
	public static void fixCase(String infile, String password) throws IOException, LoginFailedException, InterruptedException {
		
		ApiConnection conn = ApiConnection.getWikidataApiConnection();
		conn.login("PintochBot", password);
		WikibaseDataFetcher fetcher = new WikibaseDataFetcher(conn, Datamodel.SITE_WIKIDATA);
		WikibaseDataEditor wde = new WikibaseDataEditor(conn, Datamodel.SITE_WIKIDATA);
		wde.setEditAsBot(true);
		
		FileReader reader = new FileReader(new File(infile));
		LineNumberReader numbered = new LineNumberReader(reader);
		String line = numbered.readLine();
		while (line != null) {
			String[] fields = line.split("\t");
			if (fields.length != 3) {
				line = numbered.readLine();
				continue;
			}
			String qid = fields[0];
			String currentTwitterCase = fields[1];
			String preferredTwitterCase = fields[2];
			if (currentTwitterCase.equals(preferredTwitterCase) || !currentTwitterCase.toLowerCase().equals(preferredTwitterCase.toLowerCase())) {
				line = numbered.readLine();
				continue;
			}
 			
			System.out.println(qid);
			
			ItemDocument doc = null;
			try {
				doc = (ItemDocument) fetcher.getEntityDocument(qid);
			} catch (MediaWikiApiErrorException e1) {
				e1.printStackTrace();
				TimeUnit.SECONDS.sleep(10);
				line = numbered.readLine();
				continue;
			}
			
			StatementGroup group = doc.findStatementGroup(pid);
			if (group == null || group.size() != 1) {
				line = numbered.readLine();
				continue;
			}
			Statement statement = group.getStatements().get(0);
			if (statement.getClaim().getMainSnak().getValue() == null ||
			    !currentTwitterCase.equals(((StringValue)statement.getClaim().getMainSnak().getValue()).getString())) {
				line = numbered.readLine();
				continue;
			}
			Snak snak = Datamodel.makeValueSnak(pid, Datamodel.makeStringValue(preferredTwitterCase));
			Claim claim = Datamodel.makeClaim(doc.getEntityId(), snak, statement.getClaim().getQualifiers());
			Statement newStatement = Datamodel.makeStatement(
					claim, statement.getReferences(), statement.getRank(), statement.getStatementId());
					
			
			int retries = 10;
			while (retries > 0) {
				try {
					wde.updateTermsStatements(doc, Collections.emptyList(), Collections.emptyList(), Collections.emptyList(), Collections.emptyList(), 
							Collections.singletonList(newStatement), Collections.emptyList(), "change [[Property:P2002]] to canonical case");
					retries = 0;
				} catch(MediaWikiApiErrorException | NullPointerException | IOException e) {
					e.printStackTrace();
					retries--;
					Thread.sleep(10000);
				}
			}
			
			line = numbered.readLine();
		}
		numbered.close();
	}
}
