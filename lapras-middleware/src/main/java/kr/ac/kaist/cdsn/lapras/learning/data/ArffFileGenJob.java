package kr.ac.kaist.cdsn.lapras.learning.data;

/**
 * Created by chad1231 on 2017-04-20.
 */
public class ArffFileGenJob implements Runnable {
    private String fPath;
    private ArffDataset dataset;

    public ArffFileGenJob(ArffDataset dataset, String fPath){
        this.dataset = dataset;
        this.fPath = fPath;
    }

    @Override
    public void run() {

    }
}
