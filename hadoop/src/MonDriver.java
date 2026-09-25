import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.input.TextInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.mapreduce.lib.output.TextOutputFormat;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;


public class MonDriver extends Configured implements Tool {

	@Override
	public int run(String[] args) throws Exception {
		
		Job job = Job.getInstance();
		
		job.setJarByClass(MonMapper.class);
		job.setJobName("monPremierMapReduce");
		
		job.setMapperClass(MonMapper.class);
		job.setReducerClass(MonReducer.class);
		
		job.setNumReduceTasks(3);
		
		job.setMapOutputKeyClass(Text.class);
		job.setMapOutputValueClass(Text.class);
		
		job.setInputFormatClass(TextInputFormat.class);
		FileInputFormat.addInputPath(job, new Path("/mpmr/input"));
		
		job.setOutputFormatClass(TextOutputFormat.class);
		FileOutputFormat.setOutputPath(job, new Path("/mpmr/output"));
		
		job.waitForCompletion(true);
		
		return 0;
	}

	public static void main(String[] args) throws Exception {
		Configuration conf = new Configuration();
		System.exit(ToolRunner.run(conf, new MonDriver(), args));
	}

}

