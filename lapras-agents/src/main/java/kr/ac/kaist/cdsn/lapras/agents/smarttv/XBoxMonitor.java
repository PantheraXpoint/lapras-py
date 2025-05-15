package kr.ac.kaist.cdsn.lapras.agents.smarttv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class XBoxMonitor extends Thread {
    private SmartboardAgent agentImple;
    public static final String GAMER_TAG = "cdsnlab";
    private final static String USER_AGENT = "XboxAPI v2";
    private static String url = "https://xboxapi.com/v2/2533275017699527/activity";
    private static String response_msg = null;

    private boolean isRunning = false;

    public XBoxMonitor(String place, SmartboardAgent agent) {
        this.agentImple = agent;
    }

    public void run() {
        this.isRunning = true;

        while (this.isRunning) {
            try {
                String req = url;
                sendGet(req);

                agentImple.checkPlayingGames(checkingGamingTime(response_msg));
                if(checkingGamingTime(response_msg)){
                    agentImple.reportPlayingGame(checkingGame(response_msg));
                }
                Thread.sleep(60000);
            } catch (Exception e) {
                e.printStackTrace();
            }

        }
    }

    public void terminate() {
        this.isRunning = false;
        this.interrupt();
    }

    private void sendGet(String req) throws IOException {
        // TODO Auto-generated method stub
        URL obj = new URL(req);
        HttpURLConnection con = (HttpURLConnection) obj.openConnection();
        // optional default is GET
        con.setRequestMethod("GET");
        // add request header
        con.setRequestProperty("User-Agent", USER_AGENT);
        con.setRequestProperty("X-AUTH",
                "ef92c4249dbf5e29a1abc51738f4bde28ab563b9");
        con.setConnectTimeout(60000);

        // redirected?
        String redirect = con.getHeaderField("Location");
        if (redirect != null) {
            con = (HttpURLConnection) new URL(redirect).openConnection();
        }

        System.setProperty("jsse.enableSNIExtension", "false");

        BufferedReader in = new BufferedReader(
                new InputStreamReader(con.getInputStream()));

        String inputLine;
        StringBuffer response = new StringBuffer();

        while ((inputLine = in.readLine()) != null) {
            response.append(inputLine);
        }
        in.close();

        // print result
        response_msg = response.toString();
    }

    private static boolean checkingGamingTime(String json) {

        JsonObject root = new JsonParser().parse(json).getAsJsonObject();

        JsonArray subnode = root.get("activityItems").getAsJsonArray();

        JsonObject subnode_1 = subnode.get(0).getAsJsonObject();
        String subnode_2 = subnode_1.toString();

        String subnode_3 = subnode_2.substring(subnode_2.indexOf("{"),
                subnode_2.indexOf("sessionDurationInMinutes"));

        boolean gaming = false;
        if (subnode_3.contains("endTime")) {
            gaming = false;
        } else {
            gaming = true;
        }

        return gaming;
    }
    private static String checkingGame(String json){

        JsonObject root = new JsonParser().parse(json).getAsJsonObject();

        JsonArray subnode = root.get("activityItems").getAsJsonArray();

        JsonObject subnode_1 = subnode.get(0).getAsJsonObject();

        JsonElement subnode_2 = subnode_1.get("contentTitle");

        String game = subnode_2.toString();

        return game;


    }

}