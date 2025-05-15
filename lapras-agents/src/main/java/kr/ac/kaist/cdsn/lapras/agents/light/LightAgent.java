package kr.ac.kaist.cdsn.lapras.agents.light;

import com.pi4j.io.gpio.RaspiPin;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityMethod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.awt.*;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Created by Daekeun Lee on 2016-11-24.
 */
public class LightAgent extends AgentComponent implements LivoloSwitch.OnClickListener, Hue.OnInitCompleteListener {
    private static final Logger LOGGER = LoggerFactory.getLogger(LightAgent.class);

    static String[] colors = {"BLUE", "CYAN", "DARK_GRAY", "GREEN", "LIGHT_GRAY",
            "MAGENTA", "ORANGE", "PINK", "RED", "WHITE", "YELLOW"};

    private static class LightGroupInfo {
        private enum LightGroupType { HUE, RELAY };

        private String name;
        private LightGroupType type;
        private List<String> hueIds;
        private String pinName;
        private Light light;

        public LightGroupInfo(String name, LightGroupType type, List<String> hueIds) {
            if(type != LightGroupType.HUE) {
                throw new IllegalArgumentException("Only HUE type light can be initialized with hue IDs.");
            }
            this.name = name;
            this.type = type;
            this.hueIds = hueIds;
        }

        public LightGroupInfo(String name, LightGroupType type, String pinName) {
            if(type != LightGroupType.RELAY) {
                throw new IllegalArgumentException("Only RELAY type light can be initialized with pin name.");
            }
            this.name = name;
            this.type = type;
            this.pinName = pinName;
        }

        public String getName() {
            return name;
        }

        public LightGroupType getType() {
            return type;
        }

        public List<String> getHueIds() {
            return hueIds;
        }

        public String getPinName() {
            return pinName;
        }

        public Light getLight() {
            return light;
        }

        public void setLight(Light light) {
            this.light = light;
        }
    }

    private static class SwitchInfo {
        private enum ControlType { ON_OFF, COLOR, LUMINOSITY};

        private ControlType controlType;
        private List<String> targets;

        public SwitchInfo(ControlType controlType) {
            if(controlType == ControlType.ON_OFF) {
                throw new IllegalArgumentException("ON_OFF type switch cannot be initialized without target argument.");
            }
            this.controlType = controlType;
        }

        public SwitchInfo(ControlType controlType, List<String> targets) {
            if(controlType != ControlType.ON_OFF) {
                throw new IllegalArgumentException("Only ON_OFF type switch can be initialized with target argument.");
            }
            this.controlType = controlType;
            this.targets = targets;
        }

        public ControlType getControlType() {
            return controlType;
        }

        public List<String> getTargets() {
            return targets;
        }
    }

    @ContextField(publishAsUpdated = true) public Context luminosity;
    @ContextField(publishAsUpdated = true) public Context color;
    //@ContextField public Context userCount;

    private AgentConfig agentConfig;
    private Hue hue;
    private LivoloSwitch livoloSwitch;
    private final List<HueLight> hueLights = new ArrayList<>();
    private final List<LightGroupInfo> lightGroupInfos = new ArrayList<>();
    private final List<SwitchInfo> switchInfos = new ArrayList<>();
    private boolean initialized = false;

    public LightAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        agentConfig = agent.getAgentConfig();

        String[] lightGroups = agentConfig.getOptionAsArray("light_groups");
        for (String lightGroupName : lightGroups) {
            LightGroupInfo lightGroupInfo;

            LightGroupInfo.LightGroupType type = LightGroupInfo.LightGroupType.valueOf(agentConfig.getOption(lightGroupName + ".type"));
            if(type == LightGroupInfo.LightGroupType.HUE) {
                List<String> hueIds = Arrays.asList(agentConfig.getOptionAsArray(lightGroupName + ".hues"));
                lightGroupInfo = new LightGroupInfo(lightGroupName, type, hueIds);
            } else {
                String pinName = agentConfig.getOption(lightGroupName + ".pin_name");
                lightGroupInfo = new LightGroupInfo(lightGroupName, type, pinName);
            }
            lightGroupInfos.add(lightGroupInfo);
        }

        for(int i=1;i<=3;i++) { // Livolo switch has 3 switches
            String switchName = String.format("switch%d", i);
            SwitchInfo.ControlType controlType = SwitchInfo.ControlType.valueOf(agentConfig.getOption(switchName + ".control"));
            SwitchInfo switchInfo;
            if(controlType == SwitchInfo.ControlType.ON_OFF) {
                String[] targets = agentConfig.getOptionAsArray(switchName + ".targets");
                switchInfo = new SwitchInfo(controlType, Arrays.asList(targets));
            } else {
                switchInfo = new SwitchInfo(controlType);
            }
            switchInfos.add(switchInfo);
        }
    }

    @Override
    public void setUp() {
        super.setUp();

        List<List<String>> hueGroups = new ArrayList<>();
        for (LightGroupInfo lightGroupInfo : lightGroupInfos) {
            if(lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE) {
                hueGroups.add(lightGroupInfo.getHueIds());
            }
        }
        hue = new Hue(agentConfig.getOption("hue_ap_ip"),
                Integer.parseInt(agentConfig.getOption("hue_ap_port")),
                hueGroups,
                this);
        livoloSwitch = new LivoloSwitch(this);
    }

    @Override
    public void onInitComplete(List<HueLight> hueLights) {
        this.hueLights.addAll(hueLights);

        int hueLightCount = 0;
        for (LightGroupInfo lightGroupInfo : lightGroupInfos) {
            if(lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE) {
                lightGroupInfo.setLight(hueLights.get(hueLightCount));
                hueLightCount ++;
            } else {
                lightGroupInfo.setLight(new RelayLight(RaspiPin.getPinByName(lightGroupInfo.getPinName())));
            }

            // Register contexts
            contextManager.updateContext(lightGroupInfo.getName(), lightGroupInfo.getLight().isOn() ? "On" : "Off", agentName);
            contextManager.setPublishAsUpdated(lightGroupInfo.getName());

            // Register functionalities
            String onFunctionalityName = String.format("TurnOn%s", lightGroupInfo.getName());
            String offFunctionalityName = String.format("TurnOff%s", lightGroupInfo.getName());
            String toggleFunctionalityName = String.format("Toggle%s", lightGroupInfo.getName());
            functionalityExecutor.registerFunctionality(onFunctionalityName, (arguments)->{
                lightGroupInfo.getLight().turnOn();
                setColor((String) color.getValue());
                contextManager.updateContext(lightGroupInfo.getName(), "On", agentName);
            });
            functionalityExecutor.registerFunctionality(offFunctionalityName, (arguments)->{
                lightGroupInfo.getLight().turnOff();
                contextManager.updateContext(lightGroupInfo.getName(), "Off", agentName);
            });
            functionalityExecutor.registerFunctionality(toggleFunctionalityName, (arguments)->{
                lightGroupInfo.getLight().toggle();
                setColor((String) color.getValue());
                contextManager.updateContext(lightGroupInfo.getName(), lightGroupInfo.getLight().isOn() ? "On" : "Off", agentName);
            });
        }

        initialized = true;
    }

    @Override
    public void onClick(int buttonNum) {
        if (!initialized) return;

        SwitchInfo switchInfo = switchInfos.get(buttonNum-1);
        if(switchInfo.getControlType() == SwitchInfo.ControlType.ON_OFF) {
            List<LightGroupInfo> targetLightGroups = lightGroupInfos.stream()
                    .filter(lightGroupInfo -> switchInfo.getTargets().contains(lightGroupInfo.getName()))
                    .collect(Collectors.toList());

            boolean onOff = !targetLightGroups.get(0).getLight().isOn();
            for (LightGroupInfo targetLightGroup : targetLightGroups) {
                String functionalityName = String.format("Turn%s%s", onOff ? "On" : "Off", targetLightGroup.getName());
                actionManager.taken(functionalityName);
                functionalityExecutor.invokeFunctionality(functionalityName, null);
            }
        } else if(switchInfo.getControlType() == SwitchInfo.ControlType.COLOR) {
            String currentColor = (String) color.getValue();
            String newColor = "White";
            for (int i = 0; i < colors.length; i++) {
                if(colors[i].equalsIgnoreCase(currentColor)) {
                    newColor = colors[(i+1)%colors.length];
                    break;
                }
            }
            functionalityExecutor.invokeFunctionality("SetColor", new Object[]{ newColor });
            actionManager.taken("SetColor");
        } else if(switchInfo.getControlType() == SwitchInfo.ControlType.LUMINOSITY) {
            functionalityExecutor.invokeFunctionality("ChangeBrightness", null);
            actionManager.taken("ChangeBrightness");
        }
    }

    @FunctionalityMethod
    public void turnOnAllLights() {
        lightGroupInfos.forEach(lightGroupInfo -> {
            lightGroupInfo.getLight().turnOn();
            contextManager.updateContext(lightGroupInfo.getName(), "On", agentName);
        });
        setColor((String) color.getValue());
    }

    @FunctionalityMethod
    public void turnOffAllLights() {
        lightGroupInfos.forEach(lightGroupInfo -> {
            lightGroupInfo.getLight().turnOff();
            contextManager.updateContext(lightGroupInfo.getName(), "Off", agentName);
        });
    }

    @FunctionalityMethod
    public void changeLuminosity() {
        final int currentLuminosity = (int) luminosity.getValue();
        final int newLuminosity = (currentLuminosity + HueLight.DIMMING_LEVEL_UNIT > HueLight.MAXIMUM_BRIGHTNESS) ? HueLight.MINIMUM_BRIGHTNESS : currentLuminosity + HueLight.DIMMING_LEVEL_UNIT;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .map(lightGroupInfo -> (HueLight) lightGroupInfo.getLight())
                .forEach(hueLight -> {
                    hueLight.setBrightness(newLuminosity);
                });
        luminosity.updateValue(newLuminosity);
    }

    @FunctionalityMethod
    public void setLuminosityHigh() {
        final int newLuminosity = HueLight.MAXIMUM_BRIGHTNESS;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .map(lightGroupInfo -> (HueLight) lightGroupInfo.getLight())
                .forEach(hueLight -> {
                    hueLight.setBrightness(newLuminosity);
                });
        luminosity.updateValue(newLuminosity);
    }

    @FunctionalityMethod
    public void setLuminosityMedium() {
        final int newLuminosity = 124;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .map(lightGroupInfo -> (HueLight) lightGroupInfo.getLight())
                .forEach(hueLight -> {
                    hueLight.setBrightness(newLuminosity);
                });
        luminosity.updateValue(newLuminosity);
    }
    @FunctionalityMethod
    public void setLuminosityLow() {
        final int newLuminosity = 4;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .map(lightGroupInfo -> (HueLight) lightGroupInfo.getLight())
                .forEach(hueLight -> {
                    hueLight.setBrightness(newLuminosity);
                });
        luminosity.updateValue(newLuminosity);
    }

    @FunctionalityMethod
    public void setColor(String colorName) {
        Color color = null;
        switch(colorName.toLowerCase()) {
            case "black":
                color = Color.BLACK; break;
            case "blue":
                color = Color.BLUE; break;
            case "cyan":
                color = Color.CYAN; break;
            case "dark_gray":
                color = Color.DARK_GRAY; break;
            case "green":
                color = Color.GREEN; break;
            case "light_gray":
                color = Color.LIGHT_GRAY; break;
            case "magenta":
                color = Color.MAGENTA; break;
            case "orange":
                color = Color.ORANGE; break;
            case "pink":
                color = Color.PINK; break;
            case "red":
                color = Color.RED; break;
            case "white":
                color = Color.WHITE; break;
            case "yellow":
                color = Color.YELLOW; break;
        }
        if(color == null) return;

        final Color finalColor = color;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .forEach(lightGroupInfo -> ((HueLight) lightGroupInfo.getLight()).setColor(finalColor));
        this.color.updateValue(colorName.toLowerCase());
    }

    @FunctionalityMethod
    public void setBlack() {
        final Color finalColor = Color.BLACK;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .forEach(lightGroupInfo -> ((HueLight) lightGroupInfo.getLight()).setColor(finalColor));
        this.color.updateValue("black");
    }
    @FunctionalityMethod
    public void setBlue() {
        final Color finalColor = Color.BLUE;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .forEach(lightGroupInfo -> ((HueLight) lightGroupInfo.getLight()).setColor(finalColor));
        this.color.updateValue("blue");
    }
    @FunctionalityMethod
    public void setCyan() {
        final Color finalColor =Color.CYAN;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .forEach(lightGroupInfo -> ((HueLight) lightGroupInfo.getLight()).setColor(finalColor));
        this.color.updateValue("cyan");
    }
    @FunctionalityMethod
    public void setDarkGray() {
        final Color finalColor = Color.DARK_GRAY;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .forEach(lightGroupInfo -> ((HueLight) lightGroupInfo.getLight()).setColor(finalColor));
        this.color.updateValue("dark_gray");
    }
    @FunctionalityMethod
    public void setGreen() {
        final Color finalColor = Color.GREEN;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .forEach(lightGroupInfo -> ((HueLight) lightGroupInfo.getLight()).setColor(finalColor));
        this.color.updateValue("green");
    }
    @FunctionalityMethod
    public void setLightGray() {
        final Color finalColor = Color.LIGHT_GRAY;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .forEach(lightGroupInfo -> ((HueLight) lightGroupInfo.getLight()).setColor(finalColor));
        this.color.updateValue("light_gray");
    }
    @FunctionalityMethod
    public void setMagenta() {
        final Color finalColor = Color.MAGENTA;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .forEach(lightGroupInfo -> ((HueLight) lightGroupInfo.getLight()).setColor(finalColor));
        this.color.updateValue("magenta");
    }
    @FunctionalityMethod
    public void setOrange() {
        final Color finalColor = Color.ORANGE;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .forEach(lightGroupInfo -> ((HueLight) lightGroupInfo.getLight()).setColor(finalColor));
        this.color.updateValue("orange");
    }
    @FunctionalityMethod
    public void setPink() {
        final Color finalColor = Color.PINK;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .forEach(lightGroupInfo -> ((HueLight) lightGroupInfo.getLight()).setColor(finalColor));
        this.color.updateValue("pink");
    }
    @FunctionalityMethod
    public void setRed() {
        final Color finalColor = Color.RED;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .forEach(lightGroupInfo -> ((HueLight) lightGroupInfo.getLight()).setColor(finalColor));
        this.color.updateValue("red");
    }
    @FunctionalityMethod
    public void setWhite() {
        final Color finalColor = Color.WHITE;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .forEach(lightGroupInfo -> ((HueLight) lightGroupInfo.getLight()).setColor(finalColor));
        this.color.updateValue("white");
    }
    @FunctionalityMethod
    public void setYellow() {
        final Color finalColor = Color.YELLOW;
        lightGroupInfos.stream().filter(lightGroupInfo -> lightGroupInfo.getType() == LightGroupInfo.LightGroupType.HUE)
                .forEach(lightGroupInfo -> ((HueLight) lightGroupInfo.getLight()).setColor(finalColor));
        this.color.updateValue("yellow");
    }






    @Override
    public void run() {
        color.updateValue("white");
        luminosity.updateValue(HueLight.MAXIMUM_BRIGHTNESS);

        try {
            while(true) {
                Thread.sleep(Integer.MAX_VALUE);
            }
        } catch (InterruptedException e) { }
    }
}
