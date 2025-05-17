package kr.ac.kaist.cdsn.lapras.agents.fan;

import com.phidgets.IRCode;
import com.phidgets.IRCodeInfo;
import com.phidgets.PhidgetException;
import kr.ac.kaist.cdsn.lapras.agents.phidget.PhidgetIRController;

/**
 * Created by Daekeun Lee on 2017-07-28.
 */
public class FanController extends PhidgetIRController {
    private final IRCodeInfo codeInfo;

    public FanController(int serial) throws PhidgetException {
        super(serial);

        codeInfo = new IRCodeInfo(
                IRCodeInfo.ENCODING_SPACE,
                24,
                new int[]{ 4436, 4470 },
                new int[]{ 547, 582 },
                new int[]{ 547, 1963 },
                547, 108771
        );
    }

    public boolean turnOnOff() {
        return transmit(new IRCode("0f00ff", codeInfo.getBitCount()), codeInfo);
    }

    public boolean turnRotationOnOff() {
        return transmit(new IRCode("0f20df", codeInfo.getBitCount()), codeInfo);
    }

    public boolean changeIntensity() {
        return transmit(new IRCode("0f807f", codeInfo.getBitCount()), codeInfo);
    }
}
