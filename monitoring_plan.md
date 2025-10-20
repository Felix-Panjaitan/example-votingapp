# Fundamental Monitoring Plan for Voting App

## Key Components to Monitor

### AKS Cluster
- **CPU Usage**: >80% sustained for 5 minutes
- **Memory Usage**: >80% sustained for 5 minutes
- **Node Status**: Any node not in Ready state
- **Pod Status**: Failed or CrashLoopBackOff states

### PostgreSQL Database
- **CPU Usage**: >80% sustained for 5 minutes
- **Storage Usage**: >85% capacity
- **Connection Count**: Near max connections (default: 50)
- **Query Performance**: Queries taking >3 seconds

### Redis Cache
- **Memory Usage**: >90% capacity
- **Connected Clients**: Near limit
- **Cache Hit Rate**: <80%

## Monitoring Tools

- **Azure Monitor**: Primary monitoring service
- **Azure Log Analytics**: Log aggregation and queries
- **Kubernetes Dashboard**: For direct cluster visibility

## Basic Alerting Setup

1. Configure alerts in Azure Portal for each key metric
2. Set up email notifications for critical alerts
3. Use Action Groups to define escalation paths

## Essential Response Procedures

1. **High CPU/Memory**:
   - Identify resource-intensive workloads
   - Consider scaling affected component

2. **Pod/Node Failures**:
   - Check application logs
   - Review recent deployments
   - Verify network connectivity

3. **Database Issues**:
   - Check for long-running queries
   - Review connection management
   - Verify storage capacity

## Regular Monitoring Tasks

- Daily: Review error logs
- Weekly: Review performance metrics
- Monthly: Evaluate capacity and scaling needs
