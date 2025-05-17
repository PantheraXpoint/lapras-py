package kr.ac.kaist.cdsn.lapras.agents.webcam;

/**
 * Created by Hyunju Kim on 2017-03-21.
 */
import com.sun.jna.Native;
import com.sun.jna.NativeLibrary;


import uk.co.caprica.vlcj.binding.LibVlc;
import uk.co.caprica.vlcj.runtime.RuntimeUtil;

public class Constants {
    /****************** Agent-specific setting parameters ******************/
    static String AP_IP = "";
    static String POWER_MANAGER_IP = "";
    static int WEBCAM_PORT = 0;

    public static void setPlace(String placeName) {
        if ("N1SeminarRoom825".equals(placeName)) {
            AP_IP = "143.248.56.213";
            // WEBCAM_PORT = 10090; /*10090은 Light port인데 왜 이게 설정되어 있는지..
            // 모르겠음.*/
            WEBCAM_PORT = 10080;
            // N1SeminarRoom825 must use vlc-2.1.4-win64 version dll.
            NativeLibrary.addSearchPath(RuntimeUtil.getLibVlcLibraryName(), "C:\\Program Files\\VideoLAN\\VLC");
            Native.loadLibrary(RuntimeUtil.getLibVlcLibraryName(), LibVlc.class);

            Constants.POWER_MANAGER_IP = "192.168.0.103";
            Constants.WebCamHomeUrl = "http://192.168.0.163";
            Constants.videoSavedLocationOdroid = "C:\\Users\\cdsn\\RecordFiles";
            Constants.videoFileFormat = ".avi";
        } else if ("N1Lounge8F".equals(placeName)) {
            AP_IP = "143.248.53.13";
            // WEBCAM_PORT = 11720; /*11720은 Light(HUE) port인데 왜 이게 설정되어 있는지..
            // 모르겠음.*/
            WEBCAM_PORT = 11820;

            // N1Lounge8F must use vlc-2.1.4-win64 version dll.
            // this is only for N1Lounge8F.
            NativeLibrary.addSearchPath(RuntimeUtil.getLibVlcLibraryName(), "C:\\Program Files\\VideoLAN\\VLC");
            Native.loadLibrary(RuntimeUtil.getLibVlcLibraryName(), LibVlc.class);

            Constants.POWER_MANAGER_IP = "192.168.0.107";
            Constants.WebCamHomeUrl = "http://192.168.0.106";
            Constants.snapshotSavedLocationOdroid = "C:\\Users\\cdsn\\AppData\\LocalLow\\";
            // "C:\Users\cdsn\AppData\LocalLow\"; Check the directory!!
            Constants.videoSavedLocationOdroid = "C:\\Users\\cdsn\\AppData\\LocalLow\\RecordFiles";
            Constants.snapshotFileFormat = ".jpg";
            Constants.videoFileFormat = ".avi";
            Constants.videoResolution = "0.88";
        }
    }

    // Tour status : false이면 goTour off , true 이면 goTour on
    static Boolean AUTO_TOUR_STATUS = false;

    // Static setting values
    static final long TOUR_INTERVAL = 60L * 1000L; // 60 sec
    static final long AUTO_TRANSMIT_START = 5L * 1000L; // 5 sec
    static final long AUTO_TRANSMIT_INTERVAL = 24L * 60L * 60L * 1000L;  // 1 day
    static final long AUTO_RECORDING_INTERVAL = 60L * 60L * 1000L; // 60 min

    // Changeable setting values
    static String WebCamHomeUrl = "";
    static String snapshotSavedLocationOdroid = "";
    static String videoSavedLocationOdroid = "";
    static String snapshotFileFormat = "";
    static String videoFileFormat = "";
    static String videoResolution = "";

    final static String cam_webservice_id = "admin";
    final static String cam_webservice_pwd = "kaist";
    final static String ftpId = "idblab";
    final static String ftpPwd = "idblab";
    final static String ftpSnapshotDirectoryPath = "/home/snapshot/";
    final static String ftpRecordshotDirectoryPath = "/home/record/";
    final static String focusCgiUrl = "/ptz.cgi?";
    final static String imageCgiUrl = "/asp/image.cgi?";
    final static String videoCgiUrl = "/view/video.cgi?";
    final static String ftpUrl = "143.248.55.236";
    final static String focusMoveSpeed = "50";
    final static String focusRandomNumber = "0.8521266109631562";

    // Parameter List of moveFocus function
    final static String HOME = "home";
    final static String RIGHT = "right";
    final static String LEFT = "left";
    final static String UP = "up";
    final static String DOWN = "down";
    final static String RIGHTUP = "rightup";
    final static String LEFTUP = "leftup";
    final static String RIGHTDOWN = "rightdown";
    final static String LEFTDOWN = "leftdown";
    final static String TOUR_ON = "on";
    final static String TOUR_OFF = "off";

}