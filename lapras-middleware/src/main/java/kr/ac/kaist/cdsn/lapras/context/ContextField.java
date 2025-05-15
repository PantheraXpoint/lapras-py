package kr.ac.kaist.cdsn.lapras.context;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Created by Daekeun Lee on 2016-11-15.
 */
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
public @interface ContextField {
    String name() default "";
    boolean publishAsUpdated() default false;
    int publishInterval() default 0; // in seconds
}
