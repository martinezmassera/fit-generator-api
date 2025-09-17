#!/usr/bin/env python3
"""
Wrapper de Python para el SDK de Java de Garmin FIT
Permite crear archivos FIT válidos usando el SDK oficial de Java
"""

import os
import subprocess
import tempfile
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class FitJavaWrapper:
    """Wrapper para crear archivos FIT usando el SDK de Java de Garmin"""
    
    def __init__(self, java_sdk_path: str = None):
        """
        Inicializar el wrapper
        
        Args:
            java_sdk_path: Ruta al SDK de Java de Garmin
        """
        if java_sdk_path is None:
            # Usar la ruta por defecto
            java_sdk_path = "/Users/maxi/Documents/PLUGIN/FitSDKRelease_21.171.00/java"
        
        self.java_sdk_path = java_sdk_path
        self.fit_jar_path = os.path.join(java_sdk_path, "fit.jar")
        
        # Verificar que el JAR existe
        if not os.path.exists(self.fit_jar_path):
            raise FileNotFoundError(f"No se encontró fit.jar en {self.fit_jar_path}")
        
        # Verificar que Java está disponible
        try:
            subprocess.run(['java', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("Java no está disponible en el sistema")
        
        logger.info(f"FitJavaWrapper inicializado con SDK en: {java_sdk_path}")
    
    def create_workout_fit(self, routine_data: Dict[str, Any], output_path: str = None) -> str:
        """
        Crear un archivo FIT de workout usando el SDK de Java
        
        Args:
            routine_data: Datos de la rutina con formato:
                {
                    "routine_name": "Nombre de la rutina",
                    "steps": [
                        {
                            "name": "Paso 1",
                            "type": "time|distance|reps",
                            "value": "valor_numerico"
                        }
                    ]
                }
            output_path: Ruta donde guardar el archivo FIT (opcional)
        
        Returns:
            str: Ruta del archivo FIT generado
        """
        try:
            # Crear archivo temporal para los datos JSON
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_json:
                json.dump(routine_data, temp_json, indent=2)
                json_path = temp_json.name
            
            # Crear directorio temporal para el archivo FIT si no se especifica output_path
            if output_path is None:
                temp_dir = tempfile.mkdtemp()
                routine_name = routine_data.get('routine_name', 'workout').replace(' ', '_')
                output_path = os.path.join(temp_dir, f"{routine_name}.fit")
            
            # Crear el programa Java temporal
            java_code = self._generate_java_code(routine_data, output_path)
            
            # Crear archivo Java temporal con nombre fijo
            temp_dir = tempfile.mkdtemp()
            java_file_path = os.path.join(temp_dir, "FitWorkoutGenerator.java")
            with open(java_file_path, 'w') as temp_java:
                temp_java.write(java_code)
            
            # Compilar el código Java
            class_name = os.path.basename(java_file_path).replace('.java', '')
            compile_cmd = [
                'javac',
                '-cp', self.fit_jar_path,
                java_file_path
            ]
            
            logger.info(f"Compilando código Java: {' '.join(compile_cmd)}")
            compile_result = subprocess.run(compile_cmd, capture_output=True, text=True)
            
            if compile_result.returncode != 0:
                logger.error(f"Error compilando Java: {compile_result.stderr}")
                raise RuntimeError(f"Error compilando código Java: {compile_result.stderr}")
            
            # Ejecutar el código Java
            class_file_dir = os.path.dirname(java_file_path)
            class_name = os.path.splitext(os.path.basename(java_file_path))[0]
            run_cmd = [
                'java',
                '-cp', f"{self.fit_jar_path}:{class_file_dir}",
                class_name
            ]
            
            logger.info(f"Ejecutando código Java: {' '.join(run_cmd)}")
            run_result = subprocess.run(run_cmd, capture_output=True, text=True, cwd=class_file_dir)
            
            if run_result.returncode != 0:
                logger.error(f"Error ejecutando Java: {run_result.stderr}")
                raise RuntimeError(f"Error ejecutando código Java: {run_result.stderr}")
            
            logger.info(f"Archivo FIT generado exitosamente: {output_path}")
            logger.info(f"Salida Java: {run_result.stdout}")
            
            # Limpiar archivos temporales
            try:
                os.unlink(json_path)
                os.unlink(java_file_path)
                os.unlink(java_file_path.replace('.java', '.class'))
            except OSError:
                pass  # Ignorar errores de limpieza
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error creando archivo FIT: {str(e)}")
            raise
    
    def _generate_java_code(self, routine_data: Dict[str, Any], output_path: str) -> str:
        """
        Generar código Java para crear el archivo FIT
        
        Args:
            routine_data: Datos de la rutina
            output_path: Ruta donde guardar el archivo FIT
        
        Returns:
            str: Código Java generado
        """
        routine_name = routine_data.get('routine_name', 'Workout')
        steps = routine_data.get('steps', [])
        
        # Generar código para los pasos
        steps_code = []
        for i, step in enumerate(steps):
            step_name = step.get('name', f'Step {i+1}')
            step_type = step.get('type', 'time')
            step_value = step.get('value', '60')
            
            # Convertir tipo y valor según el formato del SDK
            duration_type, duration_value, target_type, target_value = self._convert_step_params(step_type, step_value)
            
            step_code = f"""
        workoutSteps.add(CreateWorkoutStep(
                {i},
                "{step_name}",
                null,
                Intensity.ACTIVE,
                {duration_type},
                {duration_value},
                {target_type},
                {target_value}));"""
            steps_code.append(step_code)
        
        steps_code_str = '\n'.join(steps_code)
        
        java_code = f"""
import com.garmin.fit.*;
import java.util.ArrayList;
import java.util.Date;
import java.util.Random;

class FitWorkoutGenerator {{
    
    public static void main(String[] args) {{
        try {{
            createWorkout();
            System.out.println("Archivo FIT generado exitosamente");
        }} catch (Exception e) {{
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }}
    }}
    
    public static void createWorkout() {{
        ArrayList<WorkoutStepMesg> workoutSteps = new ArrayList<WorkoutStepMesg>();
        
        {steps_code_str}
        
        WorkoutMesg workoutMesg = new WorkoutMesg();
        workoutMesg.setWktName("{routine_name}");
        workoutMesg.setSport(Sport.GENERIC);
        workoutMesg.setSubSport(SubSport.INVALID);
        workoutMesg.setNumValidSteps(workoutSteps.size());
        
        CreateWorkout(workoutMesg, workoutSteps);
    }}
    
    public static void CreateWorkout(WorkoutMesg workoutMesg, ArrayList<WorkoutStepMesg> workoutSteps) {{
        // The combination of file type, manufacturer id, product id, and serial number should be unique.
        File filetype = File.WORKOUT;
        short manufacturerId = Manufacturer.DEVELOPMENT;
        short productId = 0;
        Random random = new Random();
        int serialNumber = random.nextInt();

        // Every FIT file MUST contain a File ID message
        FileIdMesg fileIdMesg = new FileIdMesg();
        fileIdMesg.setType(filetype);
        fileIdMesg.setManufacturer((int) manufacturerId);
        fileIdMesg.setProduct((int) productId);
        fileIdMesg.setTimeCreated(new DateTime(new Date()));
        fileIdMesg.setSerialNumber((long) serialNumber);

        // Create the output stream
        FileEncoder encode;
        String filename = "{output_path}";

        try {{
            encode = new FileEncoder(new java.io.File(filename), Fit.ProtocolVersion.V1_0);
        }} catch (FitRuntimeException e) {{
            System.err.println("Error opening file " + filename);
            e.printStackTrace();
            return;
        }}

        // Write the messages to the file, in the proper sequence
        encode.write(fileIdMesg);
        encode.write(workoutMesg);

        for (WorkoutStepMesg workoutStep : workoutSteps) {{
            encode.write(workoutStep);
        }}

        // Close the output stream
        try {{
            encode.close();
        }} catch (FitRuntimeException e) {{
            System.err.println("Error closing encode.");
            e.printStackTrace();
            return;
        }}

        System.out.println("Encoded FIT Workout File " + filename);
    }}
    
    private static WorkoutStepMesg CreateWorkoutStep(int messageIndex,
                                                     String name,
                                                     String notes,
                                                     Intensity intensity,
                                                     WktStepDuration durationType,
                                                     Integer durationValue,
                                                     WktStepTarget targetType,
                                                     int targetValue) {{

        WorkoutStepMesg workoutStepMesg = new WorkoutStepMesg();
        workoutStepMesg.setMessageIndex(messageIndex);

        if (name != null) {{
            workoutStepMesg.setWktStepName(name);
        }}

        if (notes != null) {{
            workoutStepMesg.setNotes(notes);
        }}

        if (durationType == WktStepDuration.INVALID) {{
            return null;
        }}

        workoutStepMesg.setIntensity(intensity);
        workoutStepMesg.setDurationType(durationType);

        if (durationValue != null) {{
            workoutStepMesg.setDurationValue((long) durationValue);
        }}

        workoutStepMesg.setTargetType(targetType);
        workoutStepMesg.setTargetValue((long) targetValue);

        return workoutStepMesg;
    }}
}}
"""
        return java_code
    
    def _convert_step_params(self, step_type: str, step_value: str) -> tuple:
        """
        Convertir parámetros del paso a formato del SDK de Java
        
        Args:
            step_type: Tipo del paso (time, distance, reps)
            step_value: Valor del paso
        
        Returns:
            tuple: (duration_type, duration_value, target_type, target_value)
        """
        try:
            value = int(float(step_value))
        except (ValueError, TypeError):
            value = 60  # Valor por defecto
        
        if step_type.lower() == 'time':
            # Tiempo en segundos
            return "WktStepDuration.TIME", value, "WktStepTarget.OPEN", 0
        elif step_type.lower() == 'distance':
            # Distancia en metros (convertir de km si es necesario)
            if value < 100:  # Probablemente en km
                value = value * 1000
            return "WktStepDuration.DISTANCE", value, "WktStepTarget.OPEN", 0
        elif step_type.lower() in ['reps', 'repetitions']:
            # Repeticiones
            return "WktStepDuration.REPS", value, "WktStepTarget.OPEN", 0
        else:
            # Por defecto: tiempo
            return "WktStepDuration.TIME", value, "WktStepTarget.OPEN", 0


def test_wrapper():
    """Función de prueba para el wrapper"""
    wrapper = FitJavaWrapper()
    
    # Datos de prueba
    routine_data = {
        "routine_name": "Test Workout",
        "steps": [
            {"name": "Warm Up", "type": "time", "value": "300"},
            {"name": "Run 1km", "type": "distance", "value": "1000"},
            {"name": "Push Ups", "type": "reps", "value": "20"},
            {"name": "Cool Down", "type": "time", "value": "180"}
        ]
    }
    
    try:
        fit_file = wrapper.create_workout_fit(routine_data)
        print(f"Archivo FIT de prueba creado: {fit_file}")
        return fit_file
    except Exception as e:
        print(f"Error en prueba: {e}")
        return None


if __name__ == "__main__":
    test_wrapper()