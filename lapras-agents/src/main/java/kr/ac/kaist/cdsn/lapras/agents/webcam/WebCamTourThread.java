package kr.ac.kaist.cdsn.lapras.agents.webcam;

/**
 * Created Hyunju Kim on 2017-03-21.
 */
public class WebCamTourThread implements Runnable{
    WebCamAgent webcamAgent = null;
    long tourInterval = 60L * 1000L;

    public WebCamTourThread(WebCamAgent wcai, long interval){
        webcamAgent = wcai;
        this.tourInterval = interval;
        return;
    }

    public void run(){

        while( !(Thread.currentThread().isInterrupted()) ){
            try{
                webcamAgent.goTour();
                Thread.sleep(this.tourInterval);
            }
            catch(Exception e){
                e.printStackTrace();
                continue;
            }
        }
    }

}