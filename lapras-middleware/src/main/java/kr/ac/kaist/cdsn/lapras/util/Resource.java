package kr.ac.kaist.cdsn.lapras.util;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.InputStream;
import java.nio.file.Paths;

/**
 * Created by Daekeun Lee on 2016-11-16.
 */
public class Resource {
    public static String RESOURCE_PATH = System.getProperty("user.resourcedir");

    public static String pathOf(String resourceName) {
        return Paths.get(RESOURCE_PATH, resourceName).toString();
    }

    public static InputStream getStream(String resourceName) {
        String path = pathOf(resourceName);
        try {
            return new FileInputStream(new File(path));
        } catch (FileNotFoundException e) {
            return null;
        }
    }
}
