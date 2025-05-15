package kr.ac.kaist.cdsn.lapras.agent;

import kr.ac.kaist.cdsn.lapras.context.ContextInstance;

import javax.validation.constraints.NotNull;

/**
 * Created by Daekeun Lee on 2017-01-19.
 */
public class Context {
    private String name;
    private ContextInstance instance = null;
    private Object initialValue = null;

    private final AgentComponent agentComponent;

    public Context(@NotNull String name, ContextInstance instance, @NotNull AgentComponent agentComponent) {
        this.name = name;
        this.instance = instance;
        this.agentComponent = agentComponent;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public ContextInstance getInstance() {
        return instance;
    }

    public void setInstance(ContextInstance instance) {
        this.instance = instance;
    }

    public void setInitialValue(Object initialValue) {
        this.initialValue = initialValue;
    }

    public Object getValue() {
        return instance == null ? initialValue : instance.getValue();
    }

    public void updateValue(Object value) {
        agentComponent.contextManager.updateContext(name, value, agentComponent.agentName);
    }

    public Class getValueType() {
        return instance == null ? null : instance.getValueType();
    }
}
