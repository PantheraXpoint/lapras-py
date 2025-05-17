package kr.ac.kaist.cdsn.lapras.action;

import java.util.Arrays;

/**
 * Created by Daekeun Lee on 2017-04-10.
 *
 */
public final class Action {
    private final String name;
    private final Object[] arguments;

    public Action(String name) {
        this.name = name;
        this.arguments = null;
    }

    public Action(String name, Object[] arguments) {
        this.name = name;
        this.arguments = arguments;
    }

    public String getName() {
        return name;
    }

    public Object[] getArguments() {return arguments; }

    public boolean isStillAction() {
        return name.equals("Still");
    }

    @Override
    public boolean equals(Object other) {
        if (other instanceof Action) {
            return name.equals(((Action)other).getName()) &&
                    Arrays.equals(arguments, ((Action) other).getArguments());
        } else {
            return false;
        }
    }

    @Override
    public int hashCode() {
        return this.toString().hashCode();
    }

    public boolean isOpposite(Action action) {
        /**
         * To-do: better way? only check some cases
         */
        String n1 = action.getName().toLowerCase();
        String n2 = name.toLowerCase();
        if (n1.replace("on", "off").equals(n2) ||
                n1.replace("off", "on").equals(n2) ||
                n1.replace("up", "down").equals(n2) ||
                n1.replace("down", "up").equals(n2) ||
                n1.replace("increase", "decrease").equals(n2) ||
                n1.replace("decrease", "increase").equals(n2)) return true;
        return false;
    }

    public String toString() {
        if (arguments == null) {
            return name;
        } else {
            return name + Arrays.toString(arguments);
        }
    }
}
