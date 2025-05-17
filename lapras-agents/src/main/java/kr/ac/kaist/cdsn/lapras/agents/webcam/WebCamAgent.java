package kr.ac.kaist.cdsn.lapras.agents.webcam;
/**
 * Created by Hyunju Kim on 2017-03-21.
 */
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Authenticator;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.PasswordAuthentication;
import java.net.URL;
import java.net.URLConnection;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.Timer;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import it.sauronsoftware.ftp4j.FTPAbortedException;
import it.sauronsoftware.ftp4j.FTPClient;
import it.sauronsoftware.ftp4j.FTPDataTransferException;
import it.sauronsoftware.ftp4j.FTPException;
import it.sauronsoftware.ftp4j.FTPIllegalReplyException;

import uk.co.caprica.vlcj.player.MediaPlayer;
import uk.co.caprica.vlcj.player.MediaPlayerFactory;

/**
 * 웹캠에 접근하여 영상을 촬영하고 이를 FTP에 올리는 기능을 하는 SmartObject
 * @author Taehun Kim (iDBLab, kingmbc@gmail.com)
 * @date 2016.10.11
 * @see
 */

public class WebCamAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(WebCamAgent.class);

    /****************************************************************************************
     * AGENT IMPLEMNTATION CODE
     ****************************************************************************************/

    MediaPlayerFactory factory;
    MediaPlayer player;
    static ArrayList<String> snapshotFileList;
    static ArrayList<String> videoFileList;
    private Thread tourThread = null;
    private Timer webCamTourTimer = null;
    private Timer transmitterTimer = null;

    /*
      If place is changed, please change this value
     */
    private String placeId;

    private boolean isApplianceRunning = false;
    @ContextField(publishAsUpdated = true)
    public Context Recording;

    @ContextField(publishAsUpdated = true)
    public Context Transmitting;

    @ContextField(publishAsUpdated = true)
    public Context MoveFocus;

    public WebCamAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);
        WebCamAgent.videoFileList = new ArrayList<String>();
        WebCamAgent.snapshotFileList = new ArrayList<String>();
        authentication();

        this.placeId = agent.getAgentConfig().getPlaceName();
    }

    @Override
    public void run() {
        Constants.setPlace(this.placeId);
        if ("N1SeminarRoom825".equals(this.placeId) || "N1Lounge8F".equals(this.placeId)) {
            this.autoTransfer();
        }
        else {
            this.autoTouring(this);
        }
    }


    /**
     * @Deprecated
     * N1SeminarRoom825의 경우 PresenceSensorAgent 옆에 WebCamAgent가 설치되어 있는데,
     * 이 goTour() 기능 때문에 PresenceSensorAgent의 값에 영향을 미침.
     * 즉, 장소에 아무도 없는데 이 웹캠의 움직임 때문에 있다고 판단하는 오류를 범하게 됨
     * 따라서, http://143.248.56.213:10080/ 웹의 Tour에서 WebCam의 위치를 Center로 고정시켜놓음
     * 즉, 아래 tour_recording()이 돌더라도 좌우로 움직이지는 않음
     */
    private void autoTouring(WebCamAgent agent) {
        tourThread = new Thread(new WebCamTourThread(agent, Constants.TOUR_INTERVAL));
        tourThread.start();
        Constants.AUTO_TOUR_STATUS = true;

        webCamTourTimer = new Timer(true);
        // parameters: things that should be run when timer starts?,
        // when should it start after the beginning?(after 1hour), What is the period? (1hour)
        webCamTourTimer.schedule(new WebCamVideoRecorder(this.placeId),
                Constants.AUTO_RECORDING_INTERVAL,
                Constants.AUTO_RECORDING_INTERVAL);

//		ScheduledExecutorService service = Executors
//				.newSingleThreadScheduledExecutor();
//				service.scheduleAtFixedRate(new WebCamVideoRecorder(this.placeId), 60, 60, TimeUnit.SECONDS);
    }

    /**
     *
     */
    private void autoTransfer() {
        transmitterTimer = new Timer(true);
        // parameters: things that should be run when timer starts?,
        // when should it start after the beginning?(after 1hour), What is the period? (1hour)
        transmitterTimer.schedule(new WebCamVideoTransmitter(this.placeId),
                Constants.AUTO_TRANSMIT_START,
                Constants.AUTO_TRANSMIT_INTERVAL);
    }


    /**
     * 사진을 촬영하는 기능
     */
    public void snapshot() {
        URL url;
        URLConnection con;
        try {
            url = new URL(Constants.WebCamHomeUrl + Constants.imageCgiUrl);
            con = (URLConnection) url.openConnection();
            InputStream in = (InputStream) con.getInputStream();
            String contentType = con.getHeaderField("Content-Type");
            if (!"image/jpeg".equals(contentType)) {
                // hack: assuming it's mime if not a raw image
                int one = in.read();
                if (one == -1) {
                }
                int two = in.read();
                while (two != -1 && !(two == 10 && one == 10)) {
                    one = two;
                    two = in.read();
                }
            }
            inputStream2Disk(in);

            // Send context information(Taking Snapshot)
            Recording.updateValue("Snapshot");

        } catch (MalformedURLException e1) {
            e1.printStackTrace();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    /**
     * 디스크에 사진파일을 저장하는 기능
     */
    public void inputStream2Disk(InputStream in) throws Exception {
        // String snapshotFileName = (new
        // Long(Calendar.getInstance().getTimeInMillis())).toString();
        long time = System.currentTimeMillis();
        SimpleDateFormat dayTime = new SimpleDateFormat("yyyyMMdd HH_mm_ss");

        String snapshotFileName = this.placeId + " " + dayTime.format(new Date(time));

        WebCamAgent.snapshotFileList
                .add(Constants.snapshotSavedLocationOdroid + snapshotFileName + Constants.snapshotFileFormat);

        File outputFile = new File(
                Constants.snapshotSavedLocationOdroid + snapshotFileName + Constants.snapshotFileFormat);
        OutputStream out = new FileOutputStream(outputFile);
        byte buf[] = new byte[1024];
        int len;

        while ((len = in.read(buf)) > 0)
            out.write(buf, 0, len);
        out.close();
        in.close();

    }

    /**
     * 영상 촬영을 시작
     */

    public void recordStart() {
        factory = new MediaPlayerFactory();
        player = factory.newHeadlessMediaPlayer();

        long time = System.currentTimeMillis();
        SimpleDateFormat dayTime = new SimpleDateFormat("yyyyMMdd HH_mm_ss");
        // String videoFileName = dayTime.format(new Date(time)); // format
        // example: 20141230_11_12_04
        // String videoFileName = dayTime.format(new Date(time)) + " " +
        // WebcamAgent.PLACE_NAME; // format example: 20141230_11_12_04
        // N1SeminarRoom825

        // format example: N1SeminarRoom825 20141230_11_12_04
        String videoFileName = this.placeId + " " + dayTime.format(new Date(time));

        // String videoFileName = (new
        // Long(Calendar.getInstance().getTimeInMillis())).toString();
        String mrl = Constants.WebCamHomeUrl + Constants.videoCgiUrl + Constants.videoResolution;

        // Send context information(Start Recording)
        Recording.updateValue("Start");

        WebCamAgent.videoFileList.add(Constants.videoSavedLocationOdroid + videoFileName + Constants.videoFileFormat);
        // high quality
        // String options =
        // ":sout=#transcode{vcodec=h264,venco=x264{cfr=16},scale=1,acodec=mp4a,ab=160,channels=1,samplerate=44100}:file{dst="
        // + videoSavedLocationOdroid
        // + videoFileName
        // + "_" + WebcamAgent.PLACE_NAME
        // + videoFileFormat
        // + "}";

        String options = ":sout=#transcode{vcodec=mp1v,scale=1,acodec=mp4a,ab=160,channels=1,samplerate=44100}:file{dst="
                + Constants.videoSavedLocationOdroid + videoFileName + Constants.videoFileFormat + "}";

        player.playMedia(mrl, options);
    }

    /**
     * 영상 촬영 종료
     */

    public void recordFinish() {

        if (!(videoFileList.isEmpty())) {
            player.stop();

            // Send context information(Finish Recording)
            Recording.updateValue("Finish");


            player.release();
            factory.release();
        }

    }

    /**
     * it is developed to test move of cam at the beginning stage of development
     */
    @Deprecated
    private void moveFocus(String direction) {

        URL url;
        URLConnection con;
        authentication();
        try {
            url = new URL(Constants.WebCamHomeUrl + Constants.focusCgiUrl + "move=" + direction + "&speed="
                    + Constants.focusMoveSpeed + "&random=" + Constants.focusRandomNumber);
            System.out.println("moveFocus(String direction): " + Constants.WebCamHomeUrl + Constants.focusCgiUrl
                    + "move=" + direction + "&speed=" + Constants.focusMoveSpeed + "&random="
                    + Constants.focusRandomNumber);
            con = (URLConnection) url.openConnection();
            ((HttpURLConnection) con).getResponseCode();

        } catch (MalformedURLException e) {
            e.printStackTrace();

        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public void moveCamFocusRight() {
        URL url;
        URLConnection con;
        authentication();
        try {
            url = new URL(Constants.WebCamHomeUrl + Constants.focusCgiUrl + "move=" + Constants.RIGHT + "&speed="
                    + Constants.focusMoveSpeed + "&random=" + Constants.focusRandomNumber);
            System.out.println(
                    "moveCamFocusRight: " + Constants.WebCamHomeUrl + Constants.focusCgiUrl + "move=" + Constants.RIGHT
                            + "&speed=" + Constants.focusMoveSpeed + "&random=" + Constants.focusRandomNumber);
            con = (URLConnection) url.openConnection();
            ((HttpURLConnection) con).getResponseCode();

            // Send context information(Move Focus)
            MoveFocus.updateValue("Right");


        } catch (MalformedURLException e) {
            e.printStackTrace();

        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public void moveCamFocusLeft() {
        URL url;
        URLConnection con;
        authentication();
        try {
            url = new URL(Constants.WebCamHomeUrl + Constants.focusCgiUrl + "move=" + Constants.LEFT + "&speed="
                    + Constants.focusMoveSpeed + "&random=" + Constants.focusRandomNumber);
            System.out.println("moveCamFocusLeft: " + Constants.WebCamHomeUrl + Constants.WebCamHomeUrl
                    + Constants.focusCgiUrl + "move=" + Constants.LEFT + "&speed=" + Constants.focusMoveSpeed
                    + "&random=" + Constants.focusRandomNumber);
            con = (URLConnection) url.openConnection();
            ((HttpURLConnection) con).getResponseCode();

            // Send context information(Move Focus)
            MoveFocus.updateValue("Left");


        } catch (MalformedURLException e) {
            e.printStackTrace();

        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    public void moveCamFocusUp() {
        URL url;
        URLConnection con;
        authentication();
        try {
            url = new URL(Constants.WebCamHomeUrl + Constants.focusCgiUrl + "move=" + Constants.UP + "&speed="
                    + Constants.focusMoveSpeed + "&random=" + Constants.focusRandomNumber);
            System.out.println("moveCamFocusUp: " + Constants.WebCamHomeUrl + Constants.focusCgiUrl + "move="
                    + Constants.UP + "&speed=" + Constants.focusMoveSpeed + "&random=" + Constants.focusRandomNumber);
            con = (URLConnection) url.openConnection();
            ((HttpURLConnection) con).getResponseCode();

            // Send context information(Move Focus)
            MoveFocus.updateValue("Up");

        } catch (MalformedURLException e) {
            e.printStackTrace();

        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public void moveCamFocusDown() {
        URL url;
        URLConnection con;
        authentication();
        try {
            url = new URL(Constants.WebCamHomeUrl + Constants.focusCgiUrl + "move=" + Constants.DOWN + "&speed="
                    + Constants.focusMoveSpeed + "&random=" + Constants.focusRandomNumber);
            System.out.println("moveCamFocusDown: " + Constants.WebCamHomeUrl + Constants.focusCgiUrl + "move="
                    + Constants.DOWN + "&speed=" + Constants.focusMoveSpeed + "&random=" + Constants.focusRandomNumber);
            con = (URLConnection) url.openConnection();
            ((HttpURLConnection) con).getResponseCode();

            // Send context information(Move Focus)
            MoveFocus.updateValue("Down");

        } catch (MalformedURLException e) {
            e.printStackTrace();

        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public void moveCamFocusHome() {
        URL url;
        URLConnection con;
        authentication();
        try {
            url = new URL(Constants.WebCamHomeUrl + Constants.focusCgiUrl + "move=" + Constants.HOME + "&speed="
                    + Constants.focusMoveSpeed + "&random=" + Constants.focusRandomNumber);
            System.out.println("moveCamFocusHome: " + Constants.WebCamHomeUrl + Constants.focusCgiUrl + "move="
                    + Constants.HOME + "&speed=" + Constants.focusMoveSpeed + "&random=" + Constants.focusRandomNumber);
            con = (URLConnection) url.openConnection();
            ((HttpURLConnection) con).getResponseCode();

            // Send context information(Move Focus)
            MoveFocus.updateValue("Home");


        } catch (MalformedURLException e) {
            e.printStackTrace();

        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    /**
     * 웹캠의 시선이 좌우로 움직이게 하는 기능
     */

    public void goTour() {
        URL url;
        URLConnection con;
        authentication();
        try {
            url = new URL(Constants.WebCamHomeUrl + Constants.focusCgiUrl + "tour=" + Constants.TOUR_ON + "&tournum=0");
            System.out.println("goTour: " + Constants.WebCamHomeUrl + Constants.focusCgiUrl + "tour=on" + "&tournum=0");
            con = (URLConnection) url.openConnection();
            ((HttpURLConnection) con).getResponseCode();
            MoveFocus.updateValue("GoTour");


        } catch (MalformedURLException e) {
            e.printStackTrace();

        } catch (IOException e) {
            e.printStackTrace();
        }
    }


    public void stopTour() {
        URL url;
        URLConnection con;
        authentication();
        try {
            if (Constants.AUTO_TOUR_STATUS == true) {
                url = new URL(Constants.WebCamHomeUrl + Constants.focusCgiUrl + "tour=" + Constants.TOUR_OFF);
                System.out.println("stopTour: " + Constants.WebCamHomeUrl + Constants.focusCgiUrl + "tour=off");
                con = (URLConnection) url.openConnection();
                ((HttpURLConnection) con).getResponseCode();

                moveCamFocusHome();

                tourThread.interrupt();
                webCamTourTimer.cancel();
                Constants.AUTO_TOUR_STATUS = false;

                MoveFocus.updateValue("StopTour");

            }

        } catch (MalformedURLException e) {
            e.printStackTrace();

        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    /**
     * To manipulate the web service of IP-Camera, the ID/PWD is
     * required. This source code gives an solution for automating
     * authentication. The URL of web service is 'http://143.248.56.118:32768/'
     * which is using DDNS. The web service of current ID/PWD is 'admin/kaist'
     * and it can be changed.
     */
    public void authentication() {
        Authenticator.setDefault(new Authenticator() {
            protected PasswordAuthentication getPasswordAuthentication() {
                return new PasswordAuthentication(Constants.cam_webservice_id,
                        Constants.cam_webservice_pwd.toCharArray());
            }
        });
    }

    public boolean isApplianceRunning() {
        return isApplianceRunning;
    }

    public void setApplianceRunning(boolean b) {
        this.isApplianceRunning = b;
    }


}