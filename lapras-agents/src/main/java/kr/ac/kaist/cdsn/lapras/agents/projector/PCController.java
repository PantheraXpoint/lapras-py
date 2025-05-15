package kr.ac.kaist.cdsn.lapras.agents.projector;

/**
 * Created by gff on 2016-12-11.
 */
import java.awt.AWTException;
import java.awt.Robot;
import java.io.IOException;

public class PCController {
    public synchronized void pressKey(int keyCode) throws AWTException {
        Robot robot = new Robot();

        robot.keyPress(keyCode);

        return;
    }

    public synchronized void releaseKey(int keyCode) throws AWTException {
        Robot robot = new Robot();

        robot.keyRelease(keyCode);

        return;
    }

    public synchronized void strokeKey(int keyCode) throws AWTException {
        Robot robot = new Robot();

        robot.keyPress(keyCode);
        robot.keyRelease(keyCode);

        return;
    }

    public synchronized void killProcess(String processName) throws IOException {
        Runtime.getRuntime().exec("tskill " + processName);

        return;
    }
}
