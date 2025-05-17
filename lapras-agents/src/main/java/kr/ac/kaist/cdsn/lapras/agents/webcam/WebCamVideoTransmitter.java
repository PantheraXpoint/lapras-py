package kr.ac.kaist.cdsn.lapras.agents.webcam;
/**
 * Created Hyunju Kim on 2017-03-21.
 */
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.*;

import it.sauronsoftware.ftp4j.*;

import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;

public class WebCamVideoTransmitter extends TimerTask {
    private String placeId = null;

    @ContextField(publishAsUpdated = true)
    public Context Transmitting;

    public WebCamVideoTransmitter(String placeId) {
        this.placeId = placeId;

    }

    @Override
    public void run() {
        transmitToServer();
    }

    public void transmitToServer() {

        System.setProperty("java.net.preferIPv4Stack", "true");
        FTPClient client = new FTPClient();

        long time = System.currentTimeMillis();
        SimpleDateFormat dayTime = new SimpleDateFormat("yyyyMMdd");
        String todayString = dayTime.format(new Date(time));

        File videoDirectory = new File(Constants.videoSavedLocationOdroid);
        File[] dateDirList = videoDirectory.listFiles();
        HashMap<File, ArrayList<File>> dateVideosMap = new HashMap<>();
        for(int numDate = 0 ; numDate < dateDirList.length ; numDate++){
            File dateDir = dateDirList[numDate];
            String dateString = dateDir.getName();

            // list up folders taken before today.
            if (todayString.equals(dateString)) {
                continue;
            }

            // There is another directory in date folder which name is camera like "HSL-492641-GLULE"
            File[] camDir = dateDir.listFiles();
            File[] videoFileList = camDir[0].listFiles();

            // map date folder and files which it contains
            ArrayList<File> fileList = new ArrayList<>(Arrays.asList(videoFileList));
            dateVideosMap.put(dateDir, fileList);
        }

        try {
            client.connect(Constants.ftpUrl);
            client.login(Constants.ftpId, Constants.ftpPwd);
            client.changeDirectory(Constants.ftpRecordshotDirectoryPath + this.placeId);

            // Iterate thorugh date folders
            Iterator<File> dateKeys = dateVideosMap.keySet().iterator();
            String[] clientDateList = client.listNames();
            System.out.println("Transmission of " + todayString + " Started");
            while( dateKeys.hasNext() ){
                File dateKey = dateKeys.next();
                String dateString = dateKey.getName();
                System.out.println("Current Date directory is " + dateString);

                // Check if date folder exists in client's directory
                if (!duplicatedName(clientDateList, dateString)){
                    System.out.println("Directory " + dateString + " doesn't exist. Making such a directory");
                    client.createDirectory(dateString);
                }
                client.changeDirectory(Constants.ftpRecordshotDirectoryPath + this.placeId + "/" + dateString);

                // upload all files
                ArrayList<File> fileList = dateVideosMap.get(dateKey);
                for (int numFile = 0; numFile < fileList.size(); numFile++) {
                    File f = fileList.get(numFile);
                    System.out.println("\tUploading File named " + f.getName());
                    client.upload(f);
                    f.delete();
                }

                // Delete "HSL-492641-GLULE"
                File[] camDir = dateKey.listFiles();
                camDir[0].delete();

                // Delete date folder
                dateKey.delete();
                
                client.changeDirectoryUp();
            }

            client.disconnect(true);

        } catch (FTPDataTransferException e) {
            e.printStackTrace();
        } catch (IllegalStateException e) {
            e.printStackTrace();
        } catch (FTPIllegalReplyException e) {
            e.printStackTrace();
        } catch (FTPException e) {
            e.printStackTrace();
        } catch (FileNotFoundException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        } catch (FTPAbortedException e) {
            e.printStackTrace();
        } catch (FTPListParseException e) {
            e.printStackTrace();
        }
    }

    private boolean duplicatedName(String[] dirList, String fileDate) {
        for (String tempStr : dirList) {
            if (tempStr.equals(fileDate))
                return true;
        }
        return false;
    }

}