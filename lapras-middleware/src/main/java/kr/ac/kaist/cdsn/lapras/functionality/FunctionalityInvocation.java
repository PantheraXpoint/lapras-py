package kr.ac.kaist.cdsn.lapras.functionality;

import kr.ac.kaist.cdsn.lapras.communicator.LaprasMessage;
import kr.ac.kaist.cdsn.lapras.communicator.MessageQos;
import kr.ac.kaist.cdsn.lapras.communicator.MessageType;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Created by Daekeun Lee on 2016-11-15.
 */
public class FunctionalityInvocation extends LaprasMessage {
    private Object[] arguments;
    private boolean byUser = false;

    public FunctionalityInvocation(String name, Object[] arguments, long timestamp, String publisher) {
        super(name, timestamp, publisher);
        this.arguments = arguments;
    }

    @Override
    public String toString() {
        return String.format("%s(%s)", name, String.join(", ", (Iterable<? extends CharSequence>) Arrays.stream(arguments).map((obj)->{
            if(obj instanceof Boolean || obj instanceof Integer || obj instanceof Double || obj instanceof Float) return String.valueOf(obj);
            else if(obj instanceof String) return String.format("%s", obj);
            else return String.valueOf(obj);
        })));
    }

    public static FunctionalityInvocation fromString(String str) {
        return fromString(str, System.currentTimeMillis(), null);
    }

    public static FunctionalityInvocation fromString(String str, long timestamp, String publisher) {
        Pattern pattern = Pattern.compile("([a-z_A-Z]\\w+)\\(((?:\\s*[^ \\t\\n\\x0b\\r\\f,]+\\s*)?|(?:\\s*[^ \\t\\n\\x0b\\r\\f,]+\\s*)(?:,(?:\\s*[^ \\t\\n\\x0b\\r\\f,]+\\s*))*)\\)");
        Matcher matcher = pattern.matcher(str);
        if(!matcher.matches()) {
            throw new IllegalArgumentException("Failed to parse functionality");
        }

        String functionailtyName = matcher.group(1);

        Pattern argumentPattern = Pattern.compile("(?:\\s*([^ \\t\\n\\x0b\\r\\f,]+)\\s*)?|(?:,(?:\\s*([^ \\t\\n\\x0b\\r\\f,]+)\\s*))*");
        Matcher argumentMatcher = argumentPattern.matcher(matcher.group(2));

        List<Object> arguments = new ArrayList<>();
        while(argumentMatcher.find()) {
            if(argumentMatcher.group(1) == null) continue;
            String arg = argumentMatcher.group(1);
            if(arg.matches("(?i)true")) arguments.add(true);
            else if(arg.matches("(?i)false")) arguments.add(false);
            else if(arg.matches("\"[^\"]+\"")) arguments.add(arg.replaceAll("^\"|\"$", ""));
            else if(arg.matches("\\d+")) arguments.add(Integer.parseInt(arg));
            else if(arg.matches("\\d*\\.\\d+")) arguments.add(Double.parseDouble(arg));
            else throw new IllegalArgumentException("Failed to parse argument");
        }

        return new FunctionalityInvocation(functionailtyName, arguments.toArray(), timestamp, publisher);
    }

    public static FunctionalityInvocation fromPayload(byte[] payload) {
        return LaprasMessage.fromPayload(payload, FunctionalityInvocation.class);
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public Object[] getArguments() {
        return arguments;
    }

    public void setArguments(Object[] arguments) {
        this.arguments = arguments;
    }

    public boolean isByUser() {
        return byUser;
    }

    public void setByUser(boolean byUser) {
        this.byUser = byUser;
    }

    @Override
    public MessageType getType() {
        return MessageType.FUNCTIONALITY;
    }

    @Override
    public MessageQos getQos() {
        return MessageQos.EXACTLY_ONCE;
    }

    @Override
    public boolean getRetained() {
        return false;
    }
}
