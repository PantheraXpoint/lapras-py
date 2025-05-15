package kr.ac.kaist.cdsn.lapras.agents.light;

import com.philips.lighting.hue.sdk.PHHueSDK;
import com.philips.lighting.hue.sdk.utilities.PHUtilities;
import com.philips.lighting.model.PHBridge;
import com.philips.lighting.model.PHGroup;
import com.philips.lighting.model.PHLight;
import com.philips.lighting.model.PHLightState;

import java.awt.*;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * @auther Sanghoon Yoon (iDBLab, shygiants@gmail.com)
 * @date 2016. 7. 13.
 * @see
 */
public class HueLight extends Light {
    public static final int DIMMING_LEVEL_UNIT = 50;
    public static final int MAXIMUM_BRIGHTNESS = 254, MINIMUM_BRIGHTNESS = 4;

    private final PHGroup group;
    private final List<PHLight> lights = new ArrayList<>();
    private final PHBridge bridge = PHHueSDK.getInstance().getSelectedBridge();

    public HueLight(PHGroup group) {
        this.group = group;
        Map<String, PHLight> lights = bridge.getResourceCache().getLights();
        for (String identifier : group.getLightIdentifiers()) {
            this.lights.add(lights.get(identifier));
        }
        setColor(Color.WHITE);
    }

    private void setLightState(PHLightState lightState) {
        bridge.setLightStateForGroup(group.getIdentifier(), lightState);
    }

    @Override
    protected void setOnOff(boolean onOff) {
        PHLightState lightState = new PHLightState();
        lightState.setOn(onOff);
        setLightState(lightState);
    }

    public void setBrightness(int brightness) {
        PHLightState lightState = new PHLightState();
        lightState.setBrightness(brightness);

        setLightState(lightState);
        logger.info("Brightness changed: {}", brightness);
    }

    private int getCurrentBrightness() {
        PHLightState lightState = lights.get(0).getLastKnownLightState();
        return lightState.getBrightness();
    }

    public int turnDown() {
        int brightness = getCurrentBrightness();
        brightness -= DIMMING_LEVEL_UNIT;
        if (brightness < MINIMUM_BRIGHTNESS) {
            brightness = MINIMUM_BRIGHTNESS;
        }
        setBrightness(brightness);
        return brightness;
    }

    public int turnUp() {
        int brightness = getCurrentBrightness();
        brightness += DIMMING_LEVEL_UNIT;
        if (brightness > MAXIMUM_BRIGHTNESS) {
            brightness = MAXIMUM_BRIGHTNESS;
        }
        setBrightness(brightness);
        return brightness;
    }

    public void setColor(Color color) {
        float[] xy = PHUtilities.calculateXYFromRGB(
                color.getRed(), color.getGreen(), color.getBlue(), lights.get(0).getModelNumber());
        PHLightState lightState = new PHLightState();
        lightState.setX(xy[0]);
        lightState.setY(xy[1]);

        setLightState(lightState);
        logger.info("Color changed: RGB {}", color.getRGB());
    }
}
