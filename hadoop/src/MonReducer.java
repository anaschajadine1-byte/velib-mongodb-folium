import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Reducer;

public class MonReducer extends Reducer<Text, Text, Text, Text> {
	@Override
	protected void reduce(Text key, Iterable<Text> values,
			Reducer<Text, Text, Text, Text>.Context context) throws IOException,InterruptedException {
		
		final Map<String, Integer> occurences = new HashMap<String, Integer>();
		
		for (Text value : values) {
			String sValue = value.toString();

			//pour la clef 'salade" <=  patate, poireau, patate, lait , pain, lait,,,,

		if (occurences.containsKey(sValue)) {
       						 occurences.put(sValue, occurences.get(sValue) + 1);
    						} 
    	else {
              occurences.put(sValue, 1);
    }
		//pour la clef 'salade" <=   <patate,40><lait,12>

		//	occurences.put(sValue, occurences.containsKey(sValue) ? occurences.get(value) + 1 : 1);
		}
		
		List<String> produits = new ArrayList<String>(occurences.keySet());
		
		Collections.sort(produits, new Comparator<String>() {

			@Override
			public int compare(String o1, String o2) {
				return occurences.get(o2) - occurences.get(o1);
			}
			
		});
		
		//produits  	//pour la clef 'salade"  produits = [patate, lait,eau,;..
		
		String sProduits = "";
		for (String produit : produits) {
			sProduits += produit + ",";
		}
		
		context.write(key, new Text(sProduits)); //salade ,"patate, lait,eau,;.,,,"
		
	}
}
