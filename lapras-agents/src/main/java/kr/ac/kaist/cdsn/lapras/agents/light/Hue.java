package kr.ac.kaist.cdsn.lapras.agents.light;

import com.philips.lighting.hue.sdk.PHAccessPoint;
import com.philips.lighting.hue.sdk.PHHueSDK;
import com.philips.lighting.hue.sdk.PHMessageType;
import com.philips.lighting.hue.sdk.PHSDKListener;
import com.philips.lighting.model.PHBridge;
import com.philips.lighting.model.PHGroup;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

/**
 * @auther Sanghoon Yoon (iDBLab, shygiants@gmail.com)
 * @date 2016. 7. 13.
 * @see
 */
public final class Hue implements PHSDKListener {
    private final static Logger logger = LoggerFactory.getLogger(Hue.class);

    private static class APInfo {
        private final String ap_ip;
        private final int hue_port;

        private APInfo(String ap_ip, int port) {
            this.ap_ip = ap_ip;
            this.hue_port = port;
        }
    }

    public interface OnInitCompleteListener {
        void onInitComplete(List<HueLight> hueLights);
    }

    private final PHHueSDK phHueSDK;
    private final OnInitCompleteListener listener;
    private final List<List<String>> lightGroups;

    public Hue(final String ap_ip, final int port, final List<List<String>> lightGroups, final OnInitCompleteListener listener) {
        phHueSDK = PHHueSDK.getInstance();
        this.listener = listener;

        phHueSDK.getNotificationManager().registerSDKListener(this);

        this.lightGroups = lightGroups;
        APInfo apInfo = new APInfo(ap_ip, port);
        PHAccessPoint accessPoint = new PHAccessPoint();
        accessPoint.setIpAddress(apInfo.ap_ip + ":" + apInfo.hue_port);
        accessPoint.setUsername(LightAgent.class.getSimpleName());
        phHueSDK.connect(accessPoint);
    }

    @Override
    public void onCacheUpdated(List cacheNotificationsList, PHBridge bridge) {
        // Here you receive notifications that the BridgeResource Cache was updated. Use the PHMessageType to check
        // which cache was updated, e.g.
        if (cacheNotificationsList.contains(PHMessageType.LIGHTS_CACHE_UPDATED)) {
            logger.debug("Lights Cache Updated ");
        }
    }

    @Override
    public void onAuthenticationRequired(PHAccessPoint phAccessPoint) {
        phHueSDK.startPushlinkAuthentication(phAccessPoint);
        // Arriving here indicates that Pushlinking is required (to prove the User has physical access to the bridge).
        // Typically here you will display a pushlink image (with a timer) indicating to to the user they need to push
        // the button on their bridge within 30 seconds.
    }

    @Override
    public void onConnectionResumed(PHBridge phBridge) {

    }

    @Override
    public void onConnectionLost(PHAccessPoint phAccessPoint) {
        // Here you would handle the loss of connection to your bridge.
    }

    @Override
    public void onAccessPointsFound(List<PHAccessPoint> list) {
        // Handle your bridge search results here.  Typically if multiple results are returned you will want to display
        // them in a list and let the user select their bridge.   If one is found you may opt to connect automatically
        // to that bridge.
    }

    @Override
    public void onBridgeConnected(PHBridge phBridge, String username) {
        phHueSDK.setSelectedBridge(phBridge);
        phHueSDK.enableHeartbeat(phBridge, PHHueSDK.HB_INTERVAL);
        List<HueLight> huelights = new ArrayList<>();
        int id = 1;
        for (List<String> group : lightGroups) {
            PHGroup lightGroup = new PHGroup("Switch" + id, String.valueOf(id));
            lightGroup.setLightIdentifiers(group);
            huelights.add(new HueLight(lightGroup));
            phBridge.createGroup(lightGroup.getName(), group, null);
            logger.info("Light group {}:{} created", lightGroup.getIdentifier(), lightGroup.getName());
            id++;
        }
        listener.onInitComplete(huelights);
        // Here it is recommended to set your connected bridge in your sdk object (as above) and start the heartbeat.
        // At this point you are connected to a bridge so you should pass control to your main program/activity.
        // The username is generated randomly by the bridge.
        // Also it is recommended you store the connected IP Address/ Username in your app here.
        // This will allow easy automatic connection on subsequent use.
    }

    @Override
    public void onError(int i, String s) {
        // Here you can handle events such as Bridge Not Responding, Authentication Failed and Bridge Not Found
    }

    @Override
    public void onParsingErrors(List parsingErrorsList) {
        // Any JSON parsing errors are returned here.  Typically your program should never return these.
    }
}
