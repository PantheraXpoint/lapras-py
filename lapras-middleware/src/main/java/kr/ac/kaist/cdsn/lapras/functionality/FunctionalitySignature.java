package kr.ac.kaist.cdsn.lapras.functionality;

import kr.ac.kaist.cdsn.lapras.util.DataType;
import org.apache.commons.lang3.text.WordUtils;

import java.lang.reflect.Method;
import java.lang.reflect.Parameter;
import java.util.ArrayList;
import java.util.List;

/**
 * Created by Daekeun Lee on 2016-12-27.
 */
public class FunctionalitySignature {
    private String name;
    private List<ParameterSignature> parameters;
    private String description;

    public static class ParameterSignature {
        private String name;
        private DataType type;

        public ParameterSignature(String name, DataType type) {
            this.name = name;
            this.type = type;
        }

        public String getName() {
            return name;
        }

        public DataType getType() {
            return type;
        }
    }

    public FunctionalitySignature(String name, List<ParameterSignature> parameters, String description) {
        this.name = name;
        this.parameters = parameters;
        this.description = description;
    }

    public FunctionalitySignature() {
    }

    public static FunctionalitySignature fromMethodWithName(String functionalityName, Method method) {
        FunctionalitySignature signature = fromMethod(method);
        signature.name = functionalityName;
        return signature;
    }

    public static FunctionalitySignature fromMethod(Method method) {
        FunctionalityMethod annotation = method.getAnnotation(FunctionalityMethod.class);
        List<ParameterSignature> arguments = new ArrayList<>(method.getParameterCount());
        for (Parameter parameter : method.getParameters()) {
            arguments.add(new ParameterSignature(parameter.getName(), DataType.fromClass(parameter.getType())));
        }

        return new FunctionalitySignature(getFunctionalityName(method), arguments, (annotation == null) ? "" : annotation.description());
    }

    public static String getFunctionalityName(Method method) {
        FunctionalityMethod functionalityMethodAnnotation = method.getAnnotation(FunctionalityMethod.class);
        if(functionalityMethodAnnotation == null) {
            return WordUtils.capitalize(method.getName());
        }
        String functionalityName = functionalityMethodAnnotation.name();
        if(functionalityName.isEmpty()) {
            functionalityName = WordUtils.capitalize(method.getName());
        }
        return functionalityName;
    }

    public String getName() {
        return name;
    }

    public List<ParameterSignature> getParameters() {
        return parameters;
    }

    public String getDescription() {
        return description;
    }
}
