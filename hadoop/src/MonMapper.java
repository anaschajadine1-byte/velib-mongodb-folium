import java.io.IOException;

import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Mapper;

public class MonMapper extends Mapper<LongWritable, Text, Text, Text> {
	@Override
	protected void map(LongWritable key, Text value,
			Mapper<LongWritable, Text, Text, Text>.Context context)
			throws IOException, InterruptedException {
		
		
		String[] produits = value.toString().split(",");
		
		for (int i=0; i<produits.length; i++) {
			
			for (int j=i+1; j<produits.length; j++) {
				
				context.write(new Text(produits[i]), new Text(produits[j]));//emit 
				
			}
		}
	}
}