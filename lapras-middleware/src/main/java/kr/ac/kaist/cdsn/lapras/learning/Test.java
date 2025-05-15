package kr.ac.kaist.cdsn.lapras.learning;

import java.util.ArrayList;

/**
 * Created by chad1231 on 2017-04-19.
 */
public class Test {
    public static void main(String[] args){
        ArrayList<String> list = new ArrayList<String>();
        list.add("1");
        list.add("2");
        list.add("3");

        for(int i=0; i<list.subList(0,2).size(); i++){
            System.out.println(list.get(i));
        }
    }
}
