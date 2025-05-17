package kr.ac.kaist.cdsn.lapras.util;

import java.io.File;

/**
 * Created by Daekeun Lee on 2016-12-27.
 */
public enum DataType {
    INTEGER,
    LONG,
    FLOAT,
    STRING,
    BOOLEAN,
    FILE,
    ;

    public Class getClass(DataType type) {
        switch(type) {
            case INTEGER:   return Integer.class;
            case LONG:      return Long.class;
            case FLOAT:     return Float.class;
            case STRING:    return String.class;
            case BOOLEAN:   return Boolean.class;
            case FILE:       return File.class;
        }
        throw new IllegalArgumentException();
    }

    public static DataType fromClass(Class<?> type) {
        if(type == Integer.class) return INTEGER;
        else if(type == Long.class) return LONG;
        else if(type == Float.class) return FLOAT;
        else if(type == String.class) return STRING;
        else if(type == Boolean.class || type == boolean.class) return BOOLEAN;
        else if(type == File.class) return FILE;
        throw new IllegalArgumentException();
    }
}
