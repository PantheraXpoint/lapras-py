package kr.ac.kaist.cdsn.lapras.util;

import kr.ac.kaist.cdsn.lapras.AgentConfig;
import org.apache.commons.lang3.text.StrSubstitutor;

import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Created by Daekeun Lee on 2017-01-19.
 */
public class NameUtil {
    public static String expand(String name, AgentConfig config) {
        Map<String, String> substitutionMap = new HashMap<>();

        Pattern pattern = Pattern.compile("\\#\\{([^\\}]+)\\}");
        Matcher matcher = pattern.matcher(name);
        while(matcher.find()) {
            String variableName = matcher.group(1);
            String value = config.getOptionOrDefault(variableName, "");
            substitutionMap.put(variableName, value);
        }

        StrSubstitutor strSubstitutor = new StrSubstitutor(substitutionMap, "#{", "}");
        return strSubstitutor.replace(name);
    }
}
