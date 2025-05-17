package kr.ac.kaist.cdsn.lapras.agents.webcam;
/**
 * Created Hyunju Kim on 2017-03-21.
 */
import java.io.File;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.LinkedList;
import java.util.Queue;
import java.util.TimerTask;

import it.sauronsoftware.ftp4j.FTPClient;

import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import uk.co.caprica.vlcj.player.MediaPlayer;
import uk.co.caprica.vlcj.player.MediaPlayerFactory;

public class WebCamVideoRecorder extends TimerTask {
    private MediaPlayerFactory factory;
    private MediaPlayer player;
    private Queue<String> videoQ;
    private String placeId = null;

    @ContextField(publishAsUpdated = true)
    public Context Recording;


    public WebCamVideoRecorder(String placeId) {
        videoQ = new LinkedList<String>();
        this.placeId = placeId;

        delNeedlessVideo();
        autoRecordStart();
    }

    public void delNeedlessVideo() {
        try {
            // File dirFile = new File(WebCamAgentImpl.videoSavedLocationOdroid);
            File dirFile = new File(Constants.videoSavedLocationOdroid);
            File[] fileList = dirFile.listFiles();
            for (File f : fileList) {
                if (f.isFile()) {
                    String fileNm = f.getName();
                    int pos = fileNm.lastIndexOf(".");
                    String ext = fileNm.substring(pos + 1);
                    if ("mp4".equals(ext)) {
                        f.delete();
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void autoRecordStart() {
        factory = new MediaPlayerFactory();
        player = factory.newHeadlessMediaPlayer();

        long time = System.currentTimeMillis();
        SimpleDateFormat dayTime = new SimpleDateFormat("yyyyMMdd HH_mm_ss");

        // videoFileName format exmaple: "auto_N1SeminarRoom825 20141230 11_12_04"
        String videoFileName = "auto_" + this.placeId + " " + dayTime.format(new Date(time));

        // String mrl = WebCamAgentImpl.videoCgiUrl+ WebCamAgentImpl.videoResolution;
        String mrl = Constants.WebCamHomeUrl + Constants.videoCgiUrl + Constants.videoResolution;
        System.out.println("autoRecordStart mrl: " + mrl);
        // supAgent.reportContext(ContextType.Recording, ContextValue.Finish);
        // //TODO: cannot report here for now(20151007)

        // format=> C:\\Users\\cdsn\\AppData\\LocalLow\\auto_N1SeminarRoom825
        // 20141230 11_12_04.mp4
        // videoQ.add(WebCamAgentImpl.videoSavedLocationOdroid + videoFileName +
        // WebCamAgentImpl.videoFileFormat);
        videoQ.add(Constants.videoSavedLocationOdroid + videoFileName + Constants.videoFileFormat);

        // String options =
        // ":sout=#transcode{vcodec=mp1v,scale=1,acodec=mp4a,ab=160,channels=1,samplerate=44100}:file{dst="
        // + WebCamAgentImpl.videoSavedLocationOdroid
        // + videoFileName
        // + WebCamAgentImpl.videoFileFormat
        // + "}";
        String options = ":sout=#transcode{vcodec=mp1v,scale=1,acodec=mp4a,ab=160,channels=1,samplerate=44100}:file{dst="
                + Constants.videoSavedLocationOdroid + videoFileName + Constants.videoFileFormat + "}";

        player.playMedia(mrl,options);
    }

    public void autoRecordFinish() {
        player.stop();

        // supAgent.reportContext(ContextType.Recording, ContextValue.Finish);
        // //TODO: cannot report here for now(20151007)

        player.release();
        factory.release();
    }

    @Override
    public void run() {
        autoRecordFinish();
        new Thread(new TransferVideoRunnable()).start();
        autoRecordStart();
    }

    public class TransferVideoRunnable implements Runnable {


        public TransferVideoRunnable() {

        }

        private boolean duplicatedName(String[] dirList, String fileDate) {

            for (String tempStr : dirList) {
                if (tempStr.equals(fileDate))
                    return true;
            }

            return false;
        }

        private String getSavePath(FTPClient c, String fileDate) throws Exception {
            // currentPath examples: /home/record, /home/record/20150101
            String currentPath = c.currentDirectory();
            // dirList example: [20150101, 20150102, auto_20150102 21_29_11
            // N1Lounge8F.mp4, auto_20150102 22_29_11 N1Lounge8F.mp4, testDir]
            String[] dirList = c.listNames();

            // if ((WebCamAgentImpl.ftpRecordshotDirectoryPath +
            // WebCamAgent.PLACE_NAME).equals(currentPath)){
            if ((Constants.ftpRecordshotDirectoryPath + placeId).equals(currentPath)) {

                // fileDate 폴더가 없으면, 새 폴더 생성
                if (!duplicatedName(dirList, fileDate))
                    c.createDirectory(fileDate);

            } else {

                while (true) {
                    c.changeDirectoryUp();
                    String nowPath = c.currentDirectory();
                    // WebCamAgentImpl.videoSavedLocationOdroid와 같은 path로 경로를 맞춤.
                    // if( (WebCamAgentImpl.ftpRecordshotDirectoryPath +
                    // WebCamAgent.PLACE_NAME).equals(nowPath) )
                    if ((Constants.ftpRecordshotDirectoryPath + placeId).equals(nowPath))
                        break;
                }

                dirList = c.listNames();
                if (!duplicatedName(dirList, fileDate))
                    c.createDirectory(fileDate);
            }

            return Constants.ftpRecordshotDirectoryPath + placeId + "/" + fileDate;
        }

        private String extractDate(String fullNm) {
            // fullNm format=>
            // C:\\Users\\cdsn\\AppData\\LocalLow\\auto_N1SeminarRoom825
            // 20141230 11_12_04.mp4
            return (fullNm.split("\\s"))[1];
        }

        public void restTrans() {
            try {
                System.setProperty("java.net.preferIPv4Stack", "true");
                FTPClient client = new FTPClient();

                client.connect(Constants.ftpUrl);
                client.login(Constants.ftpId, Constants.ftpPwd);

                // ftpRecordshotDirectoryPath : "/home/record/"
                client.changeDirectory(Constants.ftpRecordshotDirectoryPath + placeId);

                for (int i = 0; i < videoQ.size() - 1;) {
                    File f = new File(videoQ.peek());

                    String fileDate = extractDate(videoQ.poll());

                    String savePath = getSavePath(client, fileDate);

                    client.changeDirectory(savePath);
                    client.upload(f);

                    f.delete();
                    Recording.updateValue("AutoRecoding");


                    // supAgent.reportContext(ContextType.Transmitting,
                    // ContextValue.VideoFile); //TODO: cannot report here for
                    // now(20151007)

                }

            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        public void run() {
            restTrans();
        }

    }

}