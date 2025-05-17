package kr.ac.kaist.cdsn.lapras.agents.projector;


import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Created by gff on 2016-12-11.
 */
public class ProjectorController {
    private static final Logger LOGGER = LoggerFactory.getLogger(ProjectorController.class);

    private static final String REQ_TARGET_FILE = "IsapiExtPj.dll";

    private String projectorIP = null;
    private int projectorPort = 0;

    public ProjectorController(String projectorIP, int projectorPort) {
        this.projectorIP = projectorIP;
        this.projectorPort = projectorPort;

        return;
    }

    public synchronized void turnOffProjector() throws IOException {
        this.sendGetRequest("D=%05%02%01%00%00%00");

        return;
    }

    public synchronized void turnOnProjector() throws IOException {
        this.sendGetRequest("D=%05%02%00%00%00%00");

        return;
    }

    public synchronized void changeInputIntoCOM1() throws IOException {
        this.sendGetRequest("D=%07%02%03%00%00%02%01%01");

        return;
    }

    public synchronized void changeInputIntoCOM2() throws IOException {
        this.sendGetRequest("D=%07%02%03%00%00%02%01%02");

        return;
    }

    public synchronized void changeInputIntoHDMI() throws IOException {
        this.sendGetRequest("D=%07%02%03%00%00%02%01%1A");

        return;
    }

    public synchronized void changeInputIntoDP() throws IOException {
        this.sendGetRequest("D=%07%02%03%00%00%02%01%1B");

        return;
    }

    public synchronized boolean isProjectorTurnedOn() throws IOException {
        String response = this.sendGetRequest("D=%06%00%BF%00%00%01%02");

        response = response.replaceAll("\\[|\\]", "").trim();
        LOGGER.debug("ProjectorTurnOn - Response to parse: {}", response);

        String[] array = response.split(",");
        if (array == null || array.length < 7) {
            return false;
        } else if ((Integer.parseInt(array[0]) & 0x80) == 0x00
                && (Integer.parseInt(array[6]) == 0x03 || Integer.parseInt(array[6]) == 0x04)) {
            return (true);
        } else {
            return (false);
        }
    }

    public synchronized InputType getInputType() throws IOException {
        String response = this.sendGetRequest("D=%06%00%BF%00%00%01%02");

        try {
            response = response.replaceAll("\\[|\\]", "").trim();
            LOGGER.debug("InputTpe - Response to parse: {}", response);

            String[] array = response.split(",");
            if (array.length < 10) {
                return null;
            }

            if ((Integer.parseInt(array[0]) & 0x80) == 0x00) {
                if (Integer.parseInt(array[9]) == 0x01) {
                    // RGB
                    return InputType.COM1;
                } else if (Integer.parseInt(array[9]) == 0x06) {
                    // HDMI
                    return InputType.HDMI;
                } else {
                    LOGGER.debug("current input bytes: {}", Integer.parseInt(array[9]));
                    return InputType.DP;
                }
            }
        } catch (Exception ex) {
            throw (new IOException());
        }
        return null;
    }

    private synchronized String sendGetRequest(String request) throws IOException {
        URL url = new URL("http://" + this.projectorIP + ":" + this.projectorPort + "/"
                + REQ_TARGET_FILE + "?" + request);
        HttpURLConnection conn = null;

        BufferedReader rd = null;
        String str = "";
        try {
            conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(10 * 1000);
            conn.setReadTimeout(10 * 1000);
            rd = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            str = "";
            String line = null;
            while ((line = rd.readLine()) != null) {
                str += line + "\n";
            }
        } catch (IOException e) {
            throw e;
        } catch (Exception e) {
            throw new IOException(e);
        } finally {
            if (rd != null) {
                rd.close();
            }
            if (conn != null) {
                conn.disconnect();
            }
        }
        return (str);
    }

}
