package kr.ac.kaist.cdsn.lapras.task;

import java.util.HashSet;
import java.util.Set;

/**
 * Created by JWP on 2018. 4. 4..
 */

public class TaskInstance {
    private int id;
    private String taskName;
    private Set<String> users;

    public TaskInstance(int id, String taskName, Set<String> users) {
        this.id = id;
        this.taskName = taskName;
        this.users = users;
    }

    public int getId() {
        return id;
    }

    public String getTaskName() {
        return taskName;
    }

    public Set<String> getUsers() {
        return users;
    }

    public static TaskInstance getIdleTask() {
        return new TaskInstance(0, "Idle", new HashSet<>());
    }
}
