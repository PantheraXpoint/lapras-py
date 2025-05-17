package kr.ac.kaist.cdsn.lapras.agents.projector;

/**
 * Created by gff on 2016-12-11.
 */
public enum ProjectorFileType {
    PDF(".pdf"), PPT(".pptx", "ppt");

    private String[] extensions;

    ProjectorFileType(String... extensions) {
        this.extensions = extensions;
    }

    public boolean containsExtension(String ext) {
        for (String s : extensions) {
            if (s.equals(ext)) {
                return true;
            }
        }
        return false;
    }

    public static ProjectorFileType getFileType(String ext) {
        if (ext == null) {
            return null;
        }

        for (ProjectorFileType type : ProjectorFileType.values()) {
            if (type.containsExtension(ext)) {
                return type;
            }
        }

        return null;
    }

}
