#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件哈希FastAPI应用
---------------
提供文件哈希计算的REST API服务
"""

import os
import time
import hashlib
import uuid
import json
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from utils.file_hash_direct import FileHashCalculator

# 创建FastAPI应用
app = FastAPI(
    title="文件哈希服务API",
    description="提供文件哈希计算服务的RESTful API",
    version="1.0.0"
)

# 存储异步任务信息
batch_tasks: Dict[str, Dict[str, Any]] = {}

# 存储异步上传文件哈希任务信息
upload_batch_tasks: Dict[str, Dict[str, Any]] = {}

# 模型定义
class HashResponse(BaseModel):
    file_name: str
    algorithm: str
    hash_value: str
    processing_time: float

class AlgorithmsResponse(BaseModel):
    algorithms: List[str]

class BatchTaskRequest(BaseModel):
    directory: str
    recursive: bool = False
    algorithm: str = "sha256"

class BatchTaskResponse(BaseModel):
    task_id: str
    status: str
    directory: str
    created_at: str

class BatchTaskStatus(BatchTaskResponse):
    completed_at: Optional[str] = None
    total_files: Optional[int] = None
    processed_files: Optional[int] = None
    success_count: Optional[int] = None
    error_count: Optional[int] = None

class FileHashResult(BaseModel):
    file_path: str
    algorithm: str
    hash_value: Optional[str] = None
    status: str
    error_message: Optional[str] = None

class BatchTaskResults(BaseModel):
    task_id: str
    directory: str
    results: List[FileHashResult]

class BatchFileHashRequest(BaseModel):
    algorithm: str = "sha256"
    chunk_size: int = 4096

class BatchFileHashResponse(BaseModel):
    results: List[HashResponse]
    total_files: int
    success_count: int
    error_count: int
    total_processing_time: float

class AsyncUploadHashRequest(BaseModel):
    algorithm: str = "sha256"
    chunk_size: int = 4096

class AsyncUploadHashResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    file_count: int

class AsyncUploadHashStatus(AsyncUploadHashResponse):
    completed_at: Optional[str] = None
    processed_files: Optional[int] = None
    success_count: Optional[int] = None
    error_count: Optional[int] = None

class FileUploadHashResult(BaseModel):
    file_name: str
    algorithm: str
    hash_value: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    processing_time: Optional[float] = None

class AsyncUploadHashResults(BaseModel):
    task_id: str
    results: List[FileUploadHashResult]
    total_files: int
    success_count: int
    error_count: int
    total_processing_time: float

class FileHashVerifyItem(BaseModel):
    expected_hash: str
    algorithm: str = "sha256"

class FileHashVerifyResult(BaseModel):
    file_name: str
    expected_hash: str
    actual_hash: str
    matched: bool
    algorithm: str
    processing_time: float

class BatchVerifyResponse(BaseModel):
    results: List[FileHashVerifyResult]
    total_files: int
    match_count: int
    mismatch_count: int
    total_processing_time: float

# API路由

@app.get("/api/v1/hash")
async def root():
    return {"message": "文件哈希计算服务API"}

@app.post("/api/v1/hash/file", response_model=HashResponse)
async def hash_file(
    file: UploadFile = File(...),
    algorithm: str = Form("sha256"),
    chunk_size: int = Form(4096)
):
    """
    计算上传文件的哈希值
    """
    if algorithm not in hashlib.algorithms_available:
        raise HTTPException(status_code=400, detail=f"不支持的哈希算法: {algorithm}")
    
    try:
        start_time = time.time()
        
        # 创建临时文件
        temp_file_path = f"/tmp/{uuid.uuid4()}"
        with open(temp_file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 计算哈希值
        calculator = FileHashCalculator(algorithm=algorithm, chunk_size=chunk_size)
        hash_value = calculator.calculate(temp_file_path)
        
        # 删除临时文件
        os.remove(temp_file_path)
        
        processing_time = time.time() - start_time
        
        return HashResponse(
            file_name=file.filename,
            algorithm=algorithm,
            hash_value=hash_value,
            processing_time=round(processing_time, 4)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文件时出错: {str(e)}")

@app.post("/api/v1/hash/files", response_model=BatchFileHashResponse)
async def hash_multiple_files(
    files: List[UploadFile] = File(...),
    algorithm: str = Form("sha256"),
    chunk_size: int = Form(4096)
):
    """
    批量计算多个上传文件的哈希值
    """
    if algorithm not in hashlib.algorithms_available:
        raise HTTPException(status_code=400, detail=f"不支持的哈希算法: {algorithm}")
    
    start_time = time.time()
    results = []
    success_count = 0
    error_count = 0
    
    for file in files:
        try:
            file_start_time = time.time()
            
            # 创建临时文件
            temp_file_path = f"/tmp/{uuid.uuid4()}"
            with open(temp_file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # 计算哈希值
            calculator = FileHashCalculator(algorithm=algorithm, chunk_size=chunk_size)
            hash_value = calculator.calculate(temp_file_path)
            
            # 删除临时文件
            os.remove(temp_file_path)
            
            file_processing_time = time.time() - file_start_time
            
            results.append(HashResponse(
                file_name=file.filename,
                algorithm=algorithm,
                hash_value=hash_value,
                processing_time=round(file_processing_time, 4)
            ))
            success_count += 1
        except Exception as e:
            error_count += 1
            # 添加错误信息到结果中
            results.append(HashResponse(
                file_name=file.filename if file.filename else "unknown",
                algorithm=algorithm,
                hash_value="error",
                processing_time=0.0
            ))
    
    total_processing_time = time.time() - start_time
    
    return BatchFileHashResponse(
        results=results,
        total_files=len(files),
        success_count=success_count,
        error_count=error_count,
        total_processing_time=round(total_processing_time, 4)
    )

@app.get("/api/v1/hash/algorithms", response_model=AlgorithmsResponse)
async def get_algorithms():
    """
    获取支持的哈希算法列表
    """
    return AlgorithmsResponse(algorithms=sorted(list(hashlib.algorithms_available)))

@app.post("/api/v1/hash/path", response_model=HashResponse)
async def hash_file_path(
    file_path: str = Form(...),
    algorithm: str = Form("sha256"),
    chunk_size: int = Form(4096)
):
    """
    计算指定路径文件的哈希值
    """
    if algorithm not in hashlib.algorithms_available:
        raise HTTPException(status_code=400, detail=f"不支持的哈希算法: {algorithm}")
    
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")
    
    try:
        start_time = time.time()
        
        # 计算哈希值
        calculator = FileHashCalculator(algorithm=algorithm, chunk_size=chunk_size)
        hash_value = calculator.calculate(file_path)
        
        processing_time = time.time() - start_time
        
        return HashResponse(
            file_name=os.path.basename(file_path),
            algorithm=algorithm,
            hash_value=hash_value,
            processing_time=round(processing_time, 4)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文件时出错: {str(e)}")

def process_directory(task_id: str, directory: str, recursive: bool, algorithm: str):
    """后台处理目录中的文件"""
    task = batch_tasks[task_id]
    task["status"] = "processing"
    
    results = []
    success_count = 0
    error_count = 0
    
    try:
        files_to_process = []
        
        # 收集要处理的文件
        if recursive:
            for root, _, files in os.walk(directory):
                for file in files:
                    files_to_process.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    files_to_process.append(file_path)
        
        task["total_files"] = len(files_to_process)
        task["processed_files"] = 0
        
        # 处理每个文件
        calculator = FileHashCalculator(algorithm=algorithm)
        for file_path in files_to_process:
            try:
                hash_value = calculator.calculate(file_path)
                results.append(FileHashResult(
                    file_path=file_path,
                    algorithm=algorithm,
                    hash_value=hash_value,
                    status="success"
                ))
                success_count += 1
            except Exception as e:
                results.append(FileHashResult(
                    file_path=file_path,
                    algorithm=algorithm,
                    status="error",
                    error_message=str(e)
                ))
                error_count += 1
            
            task["processed_files"] += 1
        
        # 更新任务状态
        task["status"] = "completed"
        task["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        task["success_count"] = success_count
        task["error_count"] = error_count
        task["results"] = results
        
    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)

@app.post("/api/v1/hash/batch", response_model=BatchTaskResponse)
async def batch_hash_files(request: BatchTaskRequest, background_tasks: BackgroundTasks):
    """
    异步处理目录中的文件
    """
    if not os.path.isdir(request.directory):
        raise HTTPException(status_code=404, detail=f"目录不存在: {request.directory}")
    
    task_id = str(uuid.uuid4())
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    task = {
        "task_id": task_id,
        "status": "pending",
        "directory": request.directory,
        "created_at": created_at,
        "algorithm": request.algorithm,
        "recursive": request.recursive
    }
    
    batch_tasks[task_id] = task
    
    # 添加后台任务
    background_tasks.add_task(
        process_directory,
        task_id,
        request.directory,
        request.recursive,
        request.algorithm
    )
    
    return BatchTaskResponse(
        task_id=task_id,
        status="pending",
        directory=request.directory,
        created_at=created_at
    )

@app.get("/api/v1/hash/batch/{task_id}", response_model=BatchTaskStatus)
async def get_batch_status(task_id: str):
    """
    获取批处理任务的状态
    """
    if task_id not in batch_tasks:
        raise HTTPException(status_code=404, detail=f"任务未找到: {task_id}")
    
    task = batch_tasks[task_id]
    
    return BatchTaskStatus(
        task_id=task_id,
        status=task["status"],
        directory=task["directory"],
        created_at=task["created_at"],
        completed_at=task.get("completed_at"),
        total_files=task.get("total_files"),
        processed_files=task.get("processed_files"),
        success_count=task.get("success_count"),
        error_count=task.get("error_count")
    )

@app.get("/api/v1/hash/batch/{task_id}/results", response_model=BatchTaskResults)
async def get_batch_results(task_id: str):
    """
    获取批处理任务的结果
    """
    if task_id not in batch_tasks:
        raise HTTPException(status_code=404, detail=f"任务未找到: {task_id}")
    
    task = batch_tasks[task_id]
    
    if task["status"] not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail=f"任务尚未完成: {task_id}")
    
    if "results" not in task:
        raise HTTPException(status_code=500, detail=f"任务结果不可用: {task_id}")
    
    return BatchTaskResults(
        task_id=task_id,
        directory=task["directory"],
        results=task["results"]
    )

async def process_uploaded_files(task_id: str, files_data: List[Dict], algorithm: str, chunk_size: int):
    """异步处理上传的文件批量计算哈希值"""
    task = upload_batch_tasks[task_id]
    task["status"] = "processing"
    
    results = []
    success_count = 0
    error_count = 0
    start_time = time.time()
    
    try:
        calculator = FileHashCalculator(algorithm=algorithm, chunk_size=chunk_size)
        task["processed_files"] = 0
        
        for file_data in files_data:
            file_start_time = time.time()
            try:
                # 计算哈希值
                hash_value = calculator.calculate(file_data["path"])
                
                results.append(FileUploadHashResult(
                    file_name=file_data["name"],
                    algorithm=algorithm,
                    hash_value=hash_value,
                    status="success",
                    processing_time=round(time.time() - file_start_time, 4)
                ))
                success_count += 1
            except Exception as e:
                results.append(FileUploadHashResult(
                    file_name=file_data["name"],
                    algorithm=algorithm,
                    status="error",
                    error_message=str(e),
                    processing_time=round(time.time() - file_start_time, 4)
                ))
                error_count += 1
            
            # 删除临时文件
            try:
                os.remove(file_data["path"])
            except:
                pass
                
            task["processed_files"] += 1
        
        total_processing_time = time.time() - start_time
        
        # 更新任务状态
        task["status"] = "completed"
        task["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        task["success_count"] = success_count
        task["error_count"] = error_count
        task["results"] = results
        task["total_processing_time"] = round(total_processing_time, 4)
        
    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)

@app.post("/api/v1/hash/upload/batch", response_model=AsyncUploadHashResponse)
async def batch_hash_uploaded_files(
    files: List[UploadFile] = File(...),
    algorithm: str = Form("sha256"),
    chunk_size: int = Form(4096),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    异步批量处理上传的文件并计算哈希值
    """
    if algorithm not in hashlib.algorithms_available:
        raise HTTPException(status_code=400, detail=f"不支持的哈希算法: {algorithm}")
    
    task_id = str(uuid.uuid4())
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # 保存上传的文件到临时位置
    files_data = []
    for file in files:
        temp_file_path = f"/tmp/{uuid.uuid4()}"
        with open(temp_file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        files_data.append({
            "name": file.filename,
            "path": temp_file_path
        })
    
    task = {
        "task_id": task_id,
        "status": "pending",
        "created_at": created_at,
        "algorithm": algorithm,
        "chunk_size": chunk_size,
        "file_count": len(files)
    }
    
    upload_batch_tasks[task_id] = task
    
    # 添加后台任务
    background_tasks.add_task(
        process_uploaded_files,
        task_id,
        files_data,
        algorithm,
        chunk_size
    )
    
    return AsyncUploadHashResponse(
        task_id=task_id,
        status="pending",
        created_at=created_at,
        file_count=len(files)
    )

@app.get("/api/v1/hash/upload/batch/{task_id}", response_model=AsyncUploadHashStatus)
async def get_upload_batch_status(task_id: str):
    """
    获取上传文件批处理任务的状态
    """
    if task_id not in upload_batch_tasks:
        raise HTTPException(status_code=404, detail=f"任务未找到: {task_id}")
    
    task = upload_batch_tasks[task_id]
    
    return AsyncUploadHashStatus(
        task_id=task_id,
        status=task["status"],
        created_at=task["created_at"],
        file_count=task["file_count"],
        completed_at=task.get("completed_at"),
        processed_files=task.get("processed_files"),
        success_count=task.get("success_count"),
        error_count=task.get("error_count")
    )

@app.get("/api/v1/hash/upload/batch/{task_id}/results", response_model=AsyncUploadHashResults)
async def get_upload_batch_results(task_id: str):
    """
    获取上传文件批处理任务的结果
    """
    if task_id not in upload_batch_tasks:
        raise HTTPException(status_code=404, detail=f"任务未找到: {task_id}")
    
    task = upload_batch_tasks[task_id]
    
    if task["status"] not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail=f"任务尚未完成: {task_id}")
    
    if "results" not in task:
        raise HTTPException(status_code=500, detail=f"任务结果不可用: {task_id}")
    
    return AsyncUploadHashResults(
        task_id=task_id,
        results=task["results"],
        total_files=task["file_count"],
        success_count=task.get("success_count", 0),
        error_count=task.get("error_count", 0),
        total_processing_time=task.get("total_processing_time", 0)
    )

@app.post("/api/v1/hash/verify", response_model=BatchVerifyResponse)
async def verify_file_hashes(
    files: List[UploadFile] = File(...),
    expected_hashes: str = Form(...),  # JSON格式的期望哈希值列表
    algorithm: str = Form("sha256"),
    chunk_size: int = Form(4096)
):
    """
    验证上传文件的哈希值是否与期望值匹配
    expected_hashes参数格式: JSON字符串 [{"file_name": "example.txt", "expected_hash": "1234..."}]
    """
    if algorithm not in hashlib.algorithms_available:
        raise HTTPException(status_code=400, detail=f"不支持的哈希算法: {algorithm}")
    
    try:
        # 解析期望的哈希值
        hash_expectations = {}
        try:
            expected_hash_list = json.loads(expected_hashes)
            for item in expected_hash_list:
                hash_expectations[item["file_name"]] = item["expected_hash"]
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="expected_hashes参数必须是有效的JSON格式")
        except KeyError:
            raise HTTPException(status_code=400, detail="expected_hashes格式错误，必须包含file_name和expected_hash字段")
        
        start_time = time.time()
        results = []
        match_count = 0
        mismatch_count = 0
        
        for file in files:
            if file.filename not in hash_expectations:
                continue
                
            try:
                file_start_time = time.time()
                
                # 创建临时文件
                temp_file_path = f"/tmp/{uuid.uuid4()}"
                with open(temp_file_path, "wb") as f:
                    content = await file.read()
                    f.write(content)
                
                # 计算哈希值
                calculator = FileHashCalculator(algorithm=algorithm, chunk_size=chunk_size)
                actual_hash = calculator.calculate(temp_file_path)
                
                # 删除临时文件
                os.remove(temp_file_path)
                
                # 验证哈希值
                expected_hash = hash_expectations[file.filename]
                matched = expected_hash.lower() == actual_hash.lower()
                
                if matched:
                    match_count += 1
                else:
                    mismatch_count += 1
                    
                file_processing_time = time.time() - file_start_time
                
                results.append(FileHashVerifyResult(
                    file_name=file.filename,
                    expected_hash=expected_hash,
                    actual_hash=actual_hash,
                    matched=matched,
                    algorithm=algorithm,
                    processing_time=round(file_processing_time, 4)
                ))
            except Exception as e:
                mismatch_count += 1
                # 添加错误信息到结果中
                results.append(FileHashVerifyResult(
                    file_name=file.filename,
                    expected_hash=hash_expectations[file.filename],
                    actual_hash="error",
                    matched=False,
                    algorithm=algorithm,
                    processing_time=0.0
                ))
        
        total_processing_time = time.time() - start_time
        
        return BatchVerifyResponse(
            results=results,
            total_files=len(results),
            match_count=match_count,
            mismatch_count=mismatch_count,
            total_processing_time=round(total_processing_time, 4)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证文件哈希值时出错: {str(e)}") 