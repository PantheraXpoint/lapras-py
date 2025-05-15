package kr.ac.kaist.cdsn.lapras.functionality;

import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;

/**
 * Created by Daekeun Lee on 2016-11-15.
 */
@Retention(RetentionPolicy.RUNTIME)
public @interface FunctionalityMethod {
    String name() default "";
    String description() default "";
}
